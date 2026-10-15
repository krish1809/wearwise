/** Names in a sentence: "Navy shirt, olive chinos and brown loafers". */
export function listed(names: string[]): string {
  const lower = names.map((name, index) =>
    index === 0 ? name : name.charAt(0).toLowerCase() + name.slice(1),
  );
  if (lower.length <= 1) return lower.join("");
  return `${lower.slice(0, -1).join(", ")} and ${lower.at(-1)}`;
}
