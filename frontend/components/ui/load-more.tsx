import { Button } from "@/components/ui/button";

type LoadMoreProps = {
  shown: number;
  total: number;
  loading?: boolean;
  onLoadMore: () => void;
};

/** The end of a long list: how much is showing, and a button for the next page. */
function LoadMore({
  shown,
  total,
  loading = false,
  onLoadMore,
}: LoadMoreProps) {
  return (
    <div
      data-slot="load-more"
      className="flex flex-col items-center gap-3 py-4"
    >
      <p className="text-sm text-ink-soft tabular-nums">
        Showing {shown} of {total}
      </p>
      {shown < total && (
        <Button variant="secondary" loading={loading} onClick={onLoadMore}>
          Load more
        </Button>
      )}
    </div>
  );
}

export { LoadMore };
