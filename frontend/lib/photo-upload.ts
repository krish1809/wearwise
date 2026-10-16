// Photos are shrunk in the browser before they're sent: the longest side to 2000 px, saved as
// JPEG. A phone photo of 5 MB becomes about half a megabyte, so uploads are quick on mobile data
// and stay far below any request size limit between here and the API. Drawing the photo onto a
// canvas also drops its metadata, so the location a phone records never leaves the device.
// The API checks and converts the file again, whatever sends it.

const MB = 1024 * 1024;
const MAX_SIDE = 2000;

/** The biggest original file accepted; it is shrunk before upload. */
export const MAX_ORIGINAL_MB = 25;

export const NOT_A_PHOTO =
  "That file isn't a photo this browser can read. Use a JPEG, PNG, or WebP image.";

/** A problem with the chosen file, described for the person. */
export class PhotoProblem extends Error {}

export function tooLarge(size: number): string | null {
  if (size <= MAX_ORIGINAL_MB * MB) return null;
  return `That file is ${(size / MB).toFixed(1)} MB. Photos can be up to ${MAX_ORIGINAL_MB} MB.`;
}

/** The file, upright, at most 2000 px on its longest side, as a JPEG without metadata. */
export async function preparePhoto(file: File): Promise<Blob> {
  if (file.type && !file.type.startsWith("image/")) {
    throw new PhotoProblem(NOT_A_PHOTO);
  }
  const large = tooLarge(file.size);
  if (large) throw new PhotoProblem(large);

  let bitmap: ImageBitmap;
  try {
    // Browsers apply the photo's rotation tag here, so the result is upright.
    bitmap = await createImageBitmap(file);
  } catch {
    throw new PhotoProblem(NOT_A_PHOTO);
  }
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new PhotoProblem(NOT_A_PHOTO);
  // JPEG has no transparency; lay transparent PNGs on white rather than black.
  context.fillStyle = "#FFFFFF";
  context.fillRect(0, 0, width, height);
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.9),
  );
  if (!blob) throw new PhotoProblem(NOT_A_PHOTO);
  return blob;
}
