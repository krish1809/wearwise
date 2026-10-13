"use client";

import { Camera, ImagePlus } from "lucide-react";
import { useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { cn } from "@/lib/utils";
import { PhotoProblem } from "@/lib/photo-upload";
import { type Photo, type PhotoRef, useUploadPhoto } from "@/lib/wardrobe";

type PhotoPickerProps = {
  photo: PhotoRef | null;
  alt: string;
  onUploaded: (photo: Photo) => void;
  onRemove: () => void;
};

/** Choose or take a photo; it uploads straight away so its colour can be suggested. */
export function PhotoPicker({
  photo,
  alt,
  onUploaded,
  onRemove,
}: PhotoPickerProps) {
  const inputId = useId();
  const errorId = useId();
  const input = useRef<HTMLInputElement>(null);
  const upload = useUploadPhoto();
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  function choose(file: File | undefined) {
    if (!file) return;
    setError(null);
    upload.mutate(file, {
      onSuccess: onUploaded,
      onError: (failure) =>
        setError(
          failure instanceof PhotoProblem
            ? failure.message
            : "Couldn't upload the photo. Check your connection and try again.",
        ),
    });
  }

  const picker = (
    <input
      ref={input}
      id={inputId}
      type="file"
      // Phones offer the camera and the gallery for image/*.
      accept="image/*"
      className="sr-only"
      aria-describedby={error ? errorId : undefined}
      onChange={(event) => {
        choose(event.target.files?.[0]);
        event.target.value = "";
      }}
    />
  );

  return (
    <div className="flex flex-col gap-2">
      {photo ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex aspect-3/4 w-40 items-center justify-center rounded-xl bg-tile p-3 *:max-h-full *:max-w-full">
            <ItemPhoto photo={photo} alt={alt} hex={null} />
          </div>
          <div className="flex flex-wrap gap-2">
            {picker}
            <Button
              type="button"
              variant="secondary"
              loading={upload.isPending}
              onClick={() => input.current?.click()}
            >
              Change photo
            </Button>
            <Button type="button" variant="quiet" onClick={onRemove}>
              Remove photo
            </Button>
          </div>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            choose(event.dataTransfer.files[0]);
          }}
          className={cn(
            "flex aspect-[4/3] max-w-sm cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed bg-tile p-6 text-center transition-colors has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-indigo",
            dragging
              ? "border-indigo bg-indigo/5"
              : "border-line-strong hover:bg-line",
            upload.isPending && "pointer-events-none",
          )}
        >
          {picker}
          {upload.isPending ? (
            <p role="status" className="text-ink-soft">
              Uploading and checking the colour…
            </p>
          ) : (
            <>
              <span aria-hidden className="flex gap-2 text-ink-soft">
                <Camera className="size-7" />
                <ImagePlus className="size-7" />
              </span>
              <span className="font-medium">Add a photo</span>
              <span className="text-sm text-ink-soft">
                Take one or choose from your photos. Lay the item flat on a
                plain background.
              </span>
            </>
          )}
        </label>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-sm text-skip">
          {error}
        </p>
      )}
    </div>
  );
}
