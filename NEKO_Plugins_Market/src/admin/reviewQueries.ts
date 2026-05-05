import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  adminApi,
  type ReviewComment,
  type ReviewCommentPayload,
  type ReviewCounts,
  type ReviewSubmission,
  type ReviewSubmissionDetail
} from "@/services/adminApi";

export const reviewKeys = {
  overview: ["admin", "review", "overview"] as const,
  submissions: (params: Record<string, unknown>) => ["admin", "review", "submissions", params] as const,
  submission: (submissionId: number | null) => ["admin", "review", "submission", submissionId] as const
};

export const REVIEW_WORKSPACE_LIST_PARAMS = { page_size: 50 } as const;
export const REVIEW_ARCHIVE_LIST_PARAMS = { status: "closed", page_size: 50 } as const;

export function useReviewOverview() {
  return useQuery({
    queryKey: reviewKeys.overview,
    queryFn: adminApi.getReviewOverview,
    staleTime: 120 * 1000
  });
}

export function useReviewSubmissions(params: Parameters<typeof adminApi.getReviewSubmissions>[0] = {}) {
  return useQuery({
    queryKey: reviewKeys.submissions(params),
    queryFn: () => adminApi.getReviewSubmissions(params),
    placeholderData: keepPreviousData,
    staleTime: 60 * 1000
  });
}

export function useReviewSubmission(submissionId: number | null) {
  return useQuery({
    queryKey: reviewKeys.submission(submissionId),
    queryFn: () => adminApi.getReviewSubmission(submissionId as number),
    enabled: submissionId !== null,
    staleTime: 60 * 1000
  });
}

export function usePrefetchReviewSubmission() {
  const queryClient = useQueryClient();

  return (submissionId: number) => queryClient.prefetchQuery({
    queryKey: reviewKeys.submission(submissionId),
    queryFn: () => adminApi.getReviewSubmission(submissionId),
    staleTime: 60 * 1000
  });
}

function countUnresolvedComments(comments: ReviewComment[]): ReviewCounts {
  return comments.reduce<ReviewCounts>((counts, comment) => {
    if (!comment.is_resolved) {
      counts.unresolved += 1;
      counts[comment.severity] += 1;
    }
    return counts;
  }, {
    critical: 0,
    major: 0,
    minor: 0,
    nitpick: 0,
    unresolved: 0
  });
}

function patchCachedComment(
  queryClient: QueryClient,
  submissionId: number,
  commentId: number,
  patchComment: (comment: ReviewComment) => ReviewComment
) {
  queryClient.setQueryData<ReviewSubmissionDetail>(reviewKeys.submission(submissionId), (current) => {
    if (!current) return current;

    let currentCaseComments: ReviewComment[] | null = null;
    const reviewCases = current.review_cases.map((reviewCase) => {
      const comments = reviewCase.comments.map((comment) => (
        comment.id === commentId ? patchComment(comment) : comment
      ));

      if (reviewCase.id === current.current_review_case_id) {
        currentCaseComments = comments;
      }

      return { ...reviewCase, comments };
    });

    return {
      ...current,
      review_cases: reviewCases,
      review_counts: currentCaseComments ? countUnresolvedComments(currentCaseComments) : current.review_counts
    };
  });
}

export function useReviewMutations(selectedSubmissionId: number | null) {
  const queryClient = useQueryClient();
  const invalidateReview = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin", "review", "overview"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "review", "submissions"] }),
      selectedSubmissionId
        ? queryClient.invalidateQueries({ queryKey: reviewKeys.submission(selectedSubmissionId) })
        : Promise.resolve()
    ]);
  };

  return {
    startReview: useMutation({
      mutationFn: ({ submissionId, note }: { submissionId: number; note?: string }) => (
        adminApi.startReviewSubmission(submissionId, note)
      ),
      onSuccess: invalidateReview
    }),
    addComment: useMutation({
      mutationFn: ({ caseId, payload }: { caseId: number; payload: ReviewCommentPayload }) => (
        adminApi.addReviewComment(caseId, payload)
      ),
      onSuccess: invalidateReview
    }),
    resolveComment: useMutation({
      mutationFn: adminApi.resolveReviewComment,
      onMutate: async (commentId) => {
        if (!selectedSubmissionId) return undefined;

        await queryClient.cancelQueries({ queryKey: reviewKeys.submission(selectedSubmissionId) });
        const previous = queryClient.getQueryData<ReviewSubmissionDetail>(reviewKeys.submission(selectedSubmissionId));
        const resolvedAt = new Date().toISOString();

        patchCachedComment(queryClient, selectedSubmissionId, commentId, (comment) => ({
          ...comment,
          is_resolved: true,
          resolved_at: resolvedAt
        }));

        return { previous };
      },
      onError: (_error, _commentId, context) => {
        if (selectedSubmissionId && context?.previous) {
          queryClient.setQueryData(reviewKeys.submission(selectedSubmissionId), context.previous);
        }
      },
      onSettled: invalidateReview
    }),
    reopenComment: useMutation({
      mutationFn: adminApi.reopenReviewComment,
      onMutate: async (commentId) => {
        if (!selectedSubmissionId) return undefined;

        await queryClient.cancelQueries({ queryKey: reviewKeys.submission(selectedSubmissionId) });
        const previous = queryClient.getQueryData<ReviewSubmissionDetail>(reviewKeys.submission(selectedSubmissionId));

        patchCachedComment(queryClient, selectedSubmissionId, commentId, (comment) => ({
          ...comment,
          is_resolved: false,
          resolved_by: null,
          resolved_at: null
        }));

        return { previous };
      },
      onError: (_error, _commentId, context) => {
        if (selectedSubmissionId && context?.previous) {
          queryClient.setQueryData(reviewKeys.submission(selectedSubmissionId), context.previous);
        }
      },
      onSettled: invalidateReview
    }),
    approveCase: useMutation({
      mutationFn: ({ caseId, summary, force }: { caseId: number; summary?: string; force?: boolean }) => (
        adminApi.approveReviewCase(caseId, { summary, force })
      ),
      onSuccess: invalidateReview
    }),
    rejectCase: useMutation({
      mutationFn: ({ caseId, summary }: { caseId: number; summary?: string }) => (
        adminApi.rejectReviewCase(caseId, { summary })
      ),
      onSuccess: invalidateReview
    })
  };
}

export function isReviewOpen(submission: ReviewSubmission) {
  return submission.status === "submitted" || submission.status === "in_review";
}
