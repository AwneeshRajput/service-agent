import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService, BookingProposal, ChatResponse, FreeSlot, Step, errorText } from './api.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  error?: boolean;
  intent?: string | null;
  steps?: Step[];
  took?: string;
  endpoint?: string;
  agents?: string[];
}

const SUGGESTIONS = [
  'my brakes are grinding',
  'any recalls on my 2019 Honda Civic?',
  'how much?',
  'book Saturday',
];

const FRIENDLY: Record<string, string> = {
  supervisor: 'Understanding your request',
  search_manuals: 'Searching our service manuals',
  diagnosis: 'Preparing your answer',
  check_recalls: 'Checking NHTSA safety recalls',
  estimate: 'Preparing your estimate',
  get_price: 'Looking up the price',
  check_slots: 'Checking available slots',
  booking_propose: 'Choosing a slot for you',
  approval: 'Waiting for your approval',
  booking_confirm: 'Confirming your booking',
  book_slot: 'Booking your slot',
  clarify: 'Preparing a question for you',
  off_topic: 'Preparing a reply',
};

function friendly(step: Step): string {
  return FRIENDLY[step.name] ?? step.name;
}

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function newSessionId(): string {
  return crypto.randomUUID().slice(0, 8);
}

@Component({
  selector: 'app-root',
  imports: [FormsModule, DatePipe, CurrencyPipe],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly api = inject(ApiService);
  private readonly scroller = viewChild<ElementRef<HTMLElement>>('scroller');

  protected readonly suggestions = SUGGESTIONS;
  protected readonly sessionId = signal(newSessionId());
  protected readonly customerId = signal(1);
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly pending = signal<BookingProposal | null>(null);
  protected readonly busy = signal(false);
  protected readonly liveSteps = signal<string[]>([]);
  protected readonly draft = signal('');

  protected readonly slotDay = signal(todayIso());
  protected readonly slotBranch = signal(0);
  protected readonly slots = signal<FreeSlot[]>([]);
  protected readonly slotsError = signal('');

  protected readonly canSend = computed(() => !this.busy() && this.pending() === null);

  constructor() {
    void this.loadSlots();
  }

  protected async send(): Promise<void> {
    await this.sendText(this.draft());
  }

  protected async sendText(text: string): Promise<void> {
    const message = text.trim();
    if (!message || !this.canSend()) {
      return;
    }
    this.messages.update((list) => [...list, { role: 'user', text: message }]);
    this.draft.set('');
    this.liveSteps.set([]);
    this.busy.set(true);
    this.scrollDown();
    try {
      const response = await this.api.chatStream(this.sessionId(), message, this.customerId(), (step) => {
        this.liveSteps.update((list) => [...list, friendly(step)]);
        this.scrollDown();
      });
      this.handle(response, 'POST /v1/chat/stream');
    } catch (error) {
      console.error(error);
      this.messages.update((list) => [...list, { role: 'assistant', text: errorText(error), error: true }]);
    } finally {
      this.busy.set(false);
      this.liveSteps.set([]);
      this.scrollDown();
    }
    await this.loadSlots();
  }

  protected async decide(approved: boolean): Promise<void> {
    this.busy.set(true);
    try {
      this.handle(await this.api.approve(this.sessionId(), approved), 'POST /v1/chat/approve');
    } catch (error) {
      console.error(error);
      const text = errorText(error);
      this.messages.update((list) => [...list, { role: 'assistant', text, error: true }]);
      if (error instanceof HttpErrorResponse && error.status === 409) {
        this.pending.set(null);
      }
    } finally {
      this.busy.set(false);
      this.scrollDown();
    }
    await this.loadSlots();
  }

  protected newConversation(): void {
    this.sessionId.set(newSessionId());
    this.messages.set([]);
    this.pending.set(null);
    this.draft.set('');
  }

  protected setSlotDay(day: string): void {
    this.slotDay.set(day);
    void this.loadSlots();
  }

  protected setSlotBranch(branch: number | null): void {
    this.slotBranch.set(branch ?? 0);
    void this.loadSlots();
  }

  private handle(response: ChatResponse, endpoint: string): void {
    const steps = response.steps ?? [];
    const agents = steps
      .filter((step) => step.kind === 'node' && step.name !== 'approval')
      .map((step) => step.label || step.name);
    const seconds = ((response.elapsed_ms ?? 0) / 1000).toFixed(1);
    this.messages.update((list) => [
      ...list,
      {
        role: 'assistant',
        text: response.answer,
        intent: response.intent,
        steps: steps.length > 0 ? steps : undefined,
        took: `${steps.length} steps, ${seconds}s`,
        endpoint,
        agents,
      },
    ]);

    const proposal = response.status === 'approval_required' ? (response.pending_booking ?? null) : null;
    this.pending.set(proposal);
    if (proposal) {
      this.slotDay.set(proposal.start_at.slice(0, 10));
      this.slotBranch.set(proposal.branch_id);
    }
  }

  private async loadSlots(): Promise<void> {
    try {
      this.slots.set(await this.api.freeSlots(this.slotDay(), this.slotBranch()));
      this.slotsError.set('');
    } catch (error) {
      this.slots.set([]);
      this.slotsError.set(errorText(error));
    }
  }

  private scrollDown(): void {
    setTimeout(() => {
      const element = this.scroller()?.nativeElement;
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    });
  }
}
