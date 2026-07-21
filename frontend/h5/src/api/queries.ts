import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  AlertsUpcomingResponse,
  Card,
  CardCreateInput,
  CardUpdateInput,
  CashProfile,
  CashflowResponse,
  DailySummaryResponse,
  MonthlyReport,
  RecommendResponse,
  ScheduleResponse,
  StopLossResponse,
  UploadConfirmInput,
  UploadConfirmResponse,
  ManualSettlement,
  ManualSettlementCreateInput,
  UploadPreview,
  User,
} from "./types";

export const queryKeys = {
  session: ["session"] as const,
  cashProfile: ["cashProfile"] as const,
  cashflow: (days = 30) => ["cashflow", days] as const,
  cards: ["cards"] as const,
  schedule: ["schedule"] as const,
  recommendations: ["recommendations"] as const,
  alertsUpcoming: ["alertsUpcoming"] as const,
  dailySummary: ["dailySummary"] as const,
  monthlyReport: ["monthlyReport"] as const,
  manualSettlements: ["manualSettlements"] as const,
};

export function useSessionQuery() {
  return useQuery<User>({
    queryKey: queryKeys.session,
    queryFn: () => apiClient<User>("/api/v1/auth/me"),
  });
}

export function useCashProfileQuery() {
  return useQuery<CashProfile>({
    queryKey: queryKeys.cashProfile,
    queryFn: () => apiClient<CashProfile>("/api/v1/profile/cash"),
  });
}

export function usePutCashMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (availableCash: string | null) =>
      apiClient<CashProfile>("/api/v1/profile/cash", {
        method: "PUT",
        body: JSON.stringify({ available_cash: availableCash }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cashflow"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.cashProfile });
    },
  });
}

export function useCashflowQuery(days = 30) {
  return useQuery<CashflowResponse>({
    queryKey: queryKeys.cashflow(days),
    queryFn: () =>
      apiClient<CashflowResponse>(`/api/v1/cashflow?days=${days}`),
  });
}

export function useCardsQuery() {
  return useQuery<Card[]>({
    queryKey: queryKeys.cards,
    queryFn: () => apiClient<Card[]>("/api/v1/cards"),
  });
}

export function useCreateCardMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CardCreateInput) =>
      apiClient<Card>("/api/v1/cards", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.cards }),
  });
}

export function useUpdateCardMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: CardUpdateInput }) =>
      apiClient<Card>(`/api/v1/cards/${id}`, {
        method: "PUT",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.cards }),
  });
}

export function useDeleteCardMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient<{ status: string }>(`/api/v1/cards/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.cards }),
  });
}

export async function previewUpload(file: File): Promise<UploadPreview> {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient<UploadPreview>("/api/v1/ingest/upload/preview", {
    method: "POST",
    body: formData,
  });
}

export function useConfirmUploadMutation() {
  return useMutation({
    mutationFn: (input: UploadConfirmInput) =>
      apiClient<UploadConfirmResponse>("/api/v1/ingest/upload/confirm", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export function useRecommendQuery(amount: number, purchaseDate: string) {
  return useQuery<RecommendResponse>({
    queryKey: ["recommendations", amount, purchaseDate],
    queryFn: () =>
      apiClient<RecommendResponse>("/api/v1/recommend", {
        method: "POST",
        body: JSON.stringify({
          purchase_date: purchaseDate,
          amount,
        }),
      }),
    enabled: amount > 0,
  });
}

export function useScheduleQuery() {
  return useQuery<ScheduleResponse>({
    queryKey: queryKeys.schedule,
    queryFn: () => apiClient<ScheduleResponse>("/api/v1/schedule"),
  });
}

export function useStopLossMutation() {
  return useMutation({
    mutationFn: ({ cardId, gapAmount }: { cardId: number; gapAmount: string }) =>
      apiClient<StopLossResponse>("/api/v1/stoploss", {
        method: "POST",
        body: JSON.stringify({ card_id: cardId, gap_amount: gapAmount }),
      }),
  });
}

export function useAlertsUpcomingQuery() {
  return useQuery<AlertsUpcomingResponse>({
    queryKey: queryKeys.alertsUpcoming,
    queryFn: () => apiClient<AlertsUpcomingResponse>("/api/v1/alerts/upcoming"),
  });
}

export function useDailySummaryQuery() {
  return useQuery<DailySummaryResponse>({
    queryKey: queryKeys.dailySummary,
    queryFn: () => apiClient<DailySummaryResponse>("/api/v1/alerts/daily-summary"),
  });
}

export function useMonthlyReportQuery() {
  return useQuery<MonthlyReport>({
    queryKey: queryKeys.monthlyReport,
    queryFn: () => apiClient<MonthlyReport>("/api/v1/report/monthly"),
  });
}


export function useManualSettlementsQuery() {
  return useQuery<ManualSettlement[]>({
    queryKey: queryKeys.manualSettlements,
    queryFn: () => apiClient<ManualSettlement[]>("/api/v1/manual-settlement"),
  });
}

export function useCreateManualSettlementMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ManualSettlementCreateInput) =>
      apiClient<ManualSettlement>("/api/v1/manual-settlement", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.manualSettlements });
      queryClient.invalidateQueries({ queryKey: ["cashflow"] });
    },
  });
}

export function useDeleteManualSettlementMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/v1/manual-settlement/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.manualSettlements });
      queryClient.invalidateQueries({ queryKey: ["cashflow"] });
    },
  });
}
