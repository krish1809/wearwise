"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import { todayIso } from "@/lib/dates";
import { WEEKDAYS, useCreateEvent } from "@/lib/plan";
import { type Profile, type Reference, useSaveProfile } from "@/lib/profile";

/** The usual occasion for each weekday, and the laundry day. */
export function UsualWeekDialog({
  profile,
  reference,
  trigger,
  open,
  onOpenChange,
}: {
  profile: Profile;
  reference: Reference;
  trigger?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const [own, setOwn] = useState(false);
  const isOpen = open ?? own;
  const setOpen = onOpenChange ?? setOwn;
  const [days, setDays] = useState<Record<string, string>>(
    profile.weekday_occasions,
  );
  const [laundry, setLaundry] = useState(
    profile.laundry_weekday === null ? "" : String(profile.laundry_weekday),
  );
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const saveProfile = useSaveProfile();
  const queryClient = useQueryClient();

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(next) => {
        setOpen(next);
        setProblem(null);
      }}
    >
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Your usual week</DialogTitle>
          <DialogDescription>
            What each day is usually for. An event on a day takes its place.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            setProblem(null);
            try {
              await saveProfile.mutateAsync({
                weekday_occasions: Object.fromEntries(
                  Object.entries(days).filter(([, occasion]) => occasion),
                ),
                laundry_weekday: laundry === "" ? null : Number(laundry),
              });
              await queryClient.invalidateQueries({ queryKey: ["plan"] });
              toast.success("Usual week saved");
              setOpen(false);
            } catch (error) {
              setProblem(problemFrom(error));
            }
          }}
        >
          {problem && <Alert tone="error">{problem.message}</Alert>}
          <div className="grid gap-3 sm:grid-cols-2">
            {WEEKDAYS.map((name, index) => (
              <Field key={name} label={name}>
                {(control) => (
                  <Select
                    value={days[String(index)] ?? ""}
                    onChange={(event) =>
                      setDays({ ...days, [String(index)]: event.target.value })
                    }
                    {...control}
                  >
                    <option value="">Nothing usual</option>
                    {reference.occasions.map((occasion) => (
                      <option key={occasion.id} value={occasion.id}>
                        {occasion.name}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ))}
          </div>
          <Field
            label="Laundry day"
            hint="From this day, the plan counts everything clean again."
            error={problem?.fields.laundry_weekday}
          >
            {(control) => (
              <Select
                value={laundry}
                onChange={(event) => setLaundry(event.target.value)}
                className="sm:max-w-xs"
                {...control}
              >
                <option value="">No fixed day</option>
                {WEEKDAYS.map((name, index) => (
                  <option key={name} value={String(index)}>
                    {name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" loading={saveProfile.isPending}>
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** A dated event with a dress code; it sets that day's occasion. */
export function EventDialog({
  reference,
  trigger,
}: {
  reference: Reference;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState(todayIso());
  const [title, setTitle] = useState("");
  const [occasion, setOccasion] = useState("");
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const create = useCreateEvent();

  function reset() {
    setDay(todayIso());
    setTitle("");
    setOccasion("");
    setProblem(null);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add an event</DialogTitle>
          <DialogDescription>
            A wedding, an interview, a trip to see family: the plan dresses that
            day for it.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            const fields: Record<string, string> = {};
            if (!title.trim()) fields.title = "Give the event a name.";
            if (!occasion) fields.occasion_id = "Choose how dressy it is.";
            if (!day) fields.day = "Choose a day.";
            if (Object.keys(fields).length) {
              setProblem({
                code: "invalid_input",
                message: "Check the highlighted fields.",
                fields,
              });
              return;
            }
            try {
              await create.mutateAsync({
                day,
                title: title.trim(),
                occasion_id: occasion,
              });
              toast.success("Event added");
              setOpen(false);
              reset();
            } catch (error) {
              setProblem(problemFrom(error));
            }
          }}
        >
          {problem && <Alert tone="error">{problem.message}</Alert>}
          <Field label="Name" error={problem?.fields.title}>
            {(control) => (
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={100}
                autoComplete="off"
                {...control}
              />
            )}
          </Field>
          <Field label="Day" error={problem?.fields.day}>
            {(control) => (
              <Input
                type="date"
                value={day}
                min={todayIso()}
                onChange={(event) => setDay(event.target.value)}
                {...control}
              />
            )}
          </Field>
          <Field label="Occasion" error={problem?.fields.occasion_id}>
            {(control) => (
              <Select
                value={occasion}
                onChange={(event) => setOccasion(event.target.value)}
                {...control}
              >
                <option value="">Choose an occasion</option>
                {reference.occasions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" loading={create.isPending}>
              Add event
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
