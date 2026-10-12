import type { ApprovedRubric, Draft, RubricSummary } from './types';

export class ApiError extends Error {}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: { message?: string };
    } | null;
    throw new ApiError(body?.detail?.message ?? 'The request could not be completed.');
  }
  return response.json() as Promise<T>;
}

export const listRubrics = () => request<RubricSummary[]>('/api/rubrics');

export const getRubric = (id: string, version: number) =>
  request<ApprovedRubric>(`/api/rubrics/${encodeURIComponent(id)}/versions/${version}`);

export const approveRubric = (draft: Draft) =>
  request<ApprovedRubric>('/api/rubrics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
  });

export const extractPdf = (file: File) => {
  const body = new FormData();
  body.append('file', file);
  return request<{ text: string }>('/api/extract', { method: 'POST', body });
};
