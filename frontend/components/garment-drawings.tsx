// Simple drawings of garments, for decoration and the style guide. They stand in for
// photos only where no real wardrobe is shown; real tiles show the person's own photos.

export function GarmentShirt() {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label="Drawing of a shirt"
      className="h-full w-full"
    >
      <path
        d="M42 18 L60 26 L78 18 L104 34 L94 54 L84 49 L84 104 L36 104 L36 49 L26 54 L16 34 Z"
        fill="#2F3E5C"
        stroke="#1B1D20"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M52 21 L60 34 L68 21"
        fill="none"
        stroke="#E8EAE7"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function GarmentTrousers() {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label="Drawing of trousers"
      className="h-full w-full"
    >
      <path
        d="M36 12 L84 12 L90 108 L68 108 L60 44 L52 108 L30 108 Z"
        fill="#C9B79C"
        stroke="#1B1D20"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M36 20 L84 20" stroke="#1B1D20" strokeWidth="1.5" />
    </svg>
  );
}

export function GarmentSneaker() {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label="Drawing of a sneaker"
      className="h-full w-full"
    >
      <path
        d="M14 72 C14 58 26 50 38 48 L52 46 L62 56 C74 60 92 62 104 70 C108 74 108 82 104 84 L18 84 C15 84 14 80 14 72 Z"
        fill="#FFFFFF"
        stroke="#1B1D20"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M14 84 L106 84 L106 90 L14 90 Z"
        fill="#D9DCD8"
        stroke="#1B1D20"
        strokeWidth="1.5"
      />
    </svg>
  );
}
