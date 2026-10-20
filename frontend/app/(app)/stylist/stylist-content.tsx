"use client";

import { MessagesSquare, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChatCardView } from "@/components/stylist/chat-card";
import { Alert } from "@/components/ui/alert";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetTrigger,
} from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import type { Reference } from "@/lib/profile";
import {
  type ChatMessage,
  type Thread,
  useAIStatus,
  useDeleteThread,
  useSend,
  useThread,
  useThreads,
} from "@/lib/stylist";
import { cn, focusRing } from "@/lib/utils";

const EXAMPLES = [
  "What should I wear to college tomorrow?",
  "Give me five outfits with my jeans.",
  "What am I missing for summer?",
  "Which of my clothes do I never wear?",
  "Is linen good for the monsoon?",
];

const OFF: Record<string, string> = {
  off: "The stylist isn't switched on in this copy of WearWise. Everything else works as usual.",
  spend_cap:
    "The stylist has used today's allowance and is back tomorrow. Everything else works as usual.",
};

export function StylistContent() {
  const status = useAIStatus();
  if (status.data && !status.data.available) {
    return (
      <Frame>
        <EmptyState icon={<Sparkles />} title="The stylist is resting">
          {OFF[status.data.reason ?? "off"] ?? OFF.off}
        </EmptyState>
      </Frame>
    );
  }
  return (
    <Frame>
      <WardrobeData>
        {({ reference }) => <Chat reference={reference} />}
      </WardrobeData>
    </Frame>
  );
}

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex max-w-5xl flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Stylist
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Ask about your own wardrobe. Answers come from your items, wear log,
          and plans; anything it suggests changing waits for you to confirm.
        </p>
      </div>
      {children}
    </div>
  );
}

function Chat({ reference }: { reference: Reference }) {
  const router = useRouter();
  const pathname = usePathname();
  const threadId = useSearchParams().get("thread");
  const threads = useThreads();
  const thread = useThread(threadId);
  const send = useSend();
  const [text, setText] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const messages = thread.data?.messages ?? [];

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, send.isPending]);

  function open(id: string | null) {
    setProblem(null);
    router.replace(id ? `${pathname}?thread=${id}` : pathname);
  }

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || send.isPending) return;
    setProblem(null);
    try {
      const sent = await send.mutateAsync({
        thread_id: threadId,
        text: trimmed,
      });
      setText("");
      if (sent.thread.id !== threadId) open(sent.thread.id);
    } catch (error) {
      // The question stays in the box to send again.
      setText(trimmed);
      setProblem(problemFrom(error).message);
    }
  }

  const list = (
    <ThreadList threads={threads.data ?? []} current={threadId} onOpen={open} />
  );

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="hidden lg:block">{list}</aside>
      <section
        aria-label="Conversation"
        className="flex min-w-0 flex-col gap-4"
      >
        <div className="flex items-center justify-between gap-3 lg:hidden">
          <BottomSheet>
            <BottomSheetTrigger asChild>
              <Button variant="secondary">
                <MessagesSquare aria-hidden />
                Conversations
              </Button>
            </BottomSheetTrigger>
            <BottomSheetContent>
              <BottomSheetHeader>
                <BottomSheetTitle>Conversations</BottomSheetTitle>
              </BottomSheetHeader>
              <div className="overflow-y-auto p-4">{list}</div>
            </BottomSheetContent>
          </BottomSheet>
          {threadId && (
            <Button variant="quiet" onClick={() => open(null)}>
              <Plus aria-hidden />
              New
            </Button>
          )}
        </div>

        <div aria-live="polite" className="flex flex-col gap-5">
          {threadId && thread.isLoading ? (
            <Skeleton className="h-40" />
          ) : messages.length === 0 && !send.isPending ? (
            <div className="rounded-xl bg-surface p-5">
              <p className="font-medium">Try asking</p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {EXAMPLES.map((example) => (
                  <li key={example}>
                    <button
                      type="button"
                      onClick={() => void ask(example)}
                      className={cn(
                        "rounded-full border border-line-strong/60 bg-paper px-3 py-1.5 text-left text-sm hover:border-ink-soft",
                        focusRing,
                      )}
                    >
                      {example}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            messages.map((message) => (
              <Bubble
                key={message.id}
                message={message}
                reference={reference}
                threadId={threadId}
              />
            ))
          )}
          {send.isPending && (
            <>
              <Bubble
                message={{
                  id: "pending",
                  role: "user",
                  text: send.variables?.text ?? "",
                  cards: [],
                  created_at: "",
                }}
                reference={reference}
                threadId={threadId}
              />
              <p
                role="status"
                className="flex items-center gap-2 text-sm text-ink-soft"
              >
                <Sparkles
                  aria-hidden
                  className="size-4 motion-safe:animate-pulse"
                />
                Looking through your wardrobe…
              </p>
            </>
          )}
          <div ref={end} />
        </div>

        {problem && <Alert tone="error">{problem}</Alert>}
        <form
          className="sticky bottom-20 flex items-end gap-2 rounded-xl bg-paper py-2 lg:bottom-4"
          onSubmit={(event) => {
            event.preventDefault();
            void ask(text);
          }}
        >
          <Textarea
            aria-label="Message"
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void ask(text);
              }
            }}
            maxLength={1000}
            rows={2}
            placeholder="Ask about your wardrobe"
            className="min-h-12 flex-1 resize-none"
          />
          <Button
            type="submit"
            size="icon"
            loading={send.isPending}
            aria-label="Send"
          >
            <Send aria-hidden />
          </Button>
        </form>
      </section>
    </div>
  );
}

function Bubble({
  message,
  reference,
  threadId,
}: {
  message: ChatMessage;
  reference: Reference;
  threadId: string | null;
}) {
  const mine = message.role === "user";
  return (
    <div
      className={cn("flex flex-col gap-2", mine ? "items-end" : "items-start")}
    >
      <p className="sr-only">{mine ? "You said:" : "The stylist said:"}</p>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-line",
          mine ? "bg-indigo/10" : "bg-surface",
        )}
      >
        {message.text}
      </div>
      {message.cards.length > 0 && (
        <ul className="flex w-full flex-col gap-3">
          {message.cards.map((card, index) => (
            <li key={index}>
              <ChatCardView
                card={card}
                reference={reference}
                threadId={threadId}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ThreadList({
  threads,
  current,
  onOpen,
}: {
  threads: Thread[];
  current: string | null;
  onOpen: (id: string | null) => void;
}) {
  const remove = useDeleteThread();
  // Deleted conversations hide at once; the deletion itself waits for the undo to pass.
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const shown = threads.filter((thread) => !hidden.has(thread.id));

  function removeThread(id: string) {
    setHidden((current) => new Set(current).add(id));
    if (id === current) onOpen(null);
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      remove.mutate(id, {
        onError: (error) => {
          setHidden((now) => {
            const next = new Set(now);
            next.delete(id);
            return next;
          });
          toast.error(problemFrom(error).message);
        },
      });
    };
    toast("Conversation deleted", {
      duration: 6000,
      action: {
        label: "Undo",
        onClick: () => {
          settled = true;
          setHidden((now) => {
            const next = new Set(now);
            next.delete(id);
            return next;
          });
        },
      },
      onAutoClose: finish,
      onDismiss: finish,
    });
  }

  return (
    <nav aria-label="Conversations" className="flex flex-col gap-1">
      <Button
        variant="secondary"
        className="mb-2 justify-start"
        onClick={() => onOpen(null)}
      >
        <Plus aria-hidden />
        New conversation
      </Button>
      {shown.length === 0 ? (
        <p className="px-3 text-sm text-ink-soft">No conversations yet.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {shown.map((thread) => (
            <li key={thread.id} className="group flex items-center gap-1">
              <Link
                href={`/stylist?thread=${thread.id}`}
                aria-current={thread.id === current ? "page" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onOpen(thread.id);
                }}
                className={cn(
                  "min-h-11 min-w-0 flex-1 truncate rounded-lg px-3 py-2.5 text-sm text-ink-soft hover:bg-tile hover:text-ink",
                  "aria-[current=page]:bg-indigo/10 aria-[current=page]:text-indigo",
                  focusRing,
                )}
              >
                {thread.title}
              </Link>
              <Button
                variant="quiet"
                size="icon"
                aria-label={`Delete ${thread.title}`}
                onClick={() => removeThread(thread.id)}
              >
                <Trash2 aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
