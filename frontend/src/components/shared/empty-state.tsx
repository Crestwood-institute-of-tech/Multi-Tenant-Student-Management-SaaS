import { Inbox } from "lucide-react";

export function EmptyState({
  title = "Nothing here yet",
  description,
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-muted-foreground">
      <Inbox className="h-8 w-8" />
      <p className="font-medium text-foreground">{title}</p>
      {description ? <p className="text-sm">{description}</p> : null}
    </div>
  );
}
