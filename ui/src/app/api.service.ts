import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface Step {
  kind: 'node' | 'tool';
  name: string;
  detail: string;
  label?: string;
  uses?: string;
}

export interface BookingProposal {
  slot_id: number;
  customer_id: number;
  service_id: number;
  service_code: string;
  service_name: string;
  branch_id: number;
  branch_name: string;
  start_at: string;
  price: number;
}

export interface ChatResponse {
  session_id: string;
  status: 'answered' | 'approval_required';
  answer: string;
  intent?: string | null;
  pending_booking?: BookingProposal | null;
  steps?: Step[];
  elapsed_ms?: number;
}

export interface FreeSlot {
  slot_id: number;
  branch_id: number;
  branch_name: string;
  bay: number;
  start_at: string;
  end_at: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

const NO_API = 'Cannot reach the API. Is uvicorn running on port 8000?';

function withStatus(status: number, detail: string): string {
  if (status === 404 || status === 405) {
    return 'The API is out of date or missing this endpoint. Restart uvicorn so it loads the latest code.';
  }
  return status ? `${detail} (error ${status})` : detail;
}

export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return withStatus(error.status, error.detail);
  }
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return NO_API;
    }
    const detail = error.error?.detail;
    return withStatus(error.status, typeof detail === 'string' ? detail : JSON.stringify(detail ?? error.message));
  }
  if (error instanceof Error) {
    return `Unexpected problem in the app: ${error.message}`;
  }
  return 'Unexpected problem in the app.';
}

async function readApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || 'Request failed';
  try {
    const body = await response.json();
    detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
  } catch {
    // keep the status text
  }
  return new ApiError(response.status, detail);
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  async chatStream(
    sessionId: string,
    message: string,
    customerId: number,
    onStep: (step: Step) => void,
  ): Promise<ChatResponse> {
    let response: Response;
    try {
      response = await fetch('/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message, customer_id: customerId }),
      });
    } catch {
      throw new ApiError(0, NO_API);
    }
    if (!response.ok || !response.body) {
      throw await readApiError(response);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result: ChatResponse | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf('\n');
      while (newline >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf('\n');
        if (!line) {
          continue;
        }
        const event = JSON.parse(line);
        if (event.type === 'step') {
          onStep(event.step as Step);
        } else if (event.type === 'result') {
          result = event.response as ChatResponse;
        } else if (event.type === 'error') {
          throw new ApiError(event.status, String(event.detail));
        }
      }
    }

    if (!result) {
      throw new ApiError(0, 'The connection closed before the assistant finished. Please try again.');
    }
    return result;
  }

  approve(sessionId: string, approved: boolean): Promise<ChatResponse> {
    return firstValueFrom(
      this.http.post<ChatResponse>('/v1/chat/approve', { session_id: sessionId, approved }),
    );
  }

  freeSlots(day: string, branchId: number): Promise<FreeSlot[]> {
    let params = new HttpParams().set('date', day);
    if (branchId) {
      params = params.set('branch_id', branchId);
    }
    return firstValueFrom(this.http.get<FreeSlot[]>('/v1/slots/free', { params }));
  }
}
