"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import { readApiError } from "@/lib/api/errors";
import { meQueryKey } from "@/lib/auth";

const SECTIONS = [
  { id: "menswear", name: "A menswear wardrobe" },
  { id: "womenswear", name: "A womenswear wardrobe" },
] as const;

/**
 * A fresh sample wardrobe of the visitor's own, logged in at once, with no sign-up. It's
 * deleted a day later.
 */
export function DemoButton() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [starting, setStarting] = useState(false);

  async function start(section: (typeof SECTIONS)[number]["id"]) {
    setStarting(true);
    try {
      const { data, error } = await api.POST("/api/v1/auth/demo", {
        body: { section },
      });
      if (!data) {
        toast.error(readApiError(error).message);
        return;
      }
      queryClient.setQueryData(meQueryKey, data);
      router.push("/home");
    } catch {
      toast.error(
        "Couldn't start the demo. Check your connection and try again.",
      );
    } finally {
      setStarting(false);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" loading={starting}>
          Try the demo
          <ChevronDown aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Start with</DropdownMenuLabel>
        {SECTIONS.map((section) => (
          <DropdownMenuItem
            key={section.id}
            onSelect={() => void start(section.id)}
          >
            {section.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
