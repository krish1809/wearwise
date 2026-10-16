// jsdom leaves out some browser APIs that Radix components call. These stand-ins do nothing,
// which is enough for tests that check behaviour rather than layout.

class ResizeObserverStandIn {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver ??= ResizeObserverStandIn;
