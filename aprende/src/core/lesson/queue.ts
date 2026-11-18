/* The lesson player's order of play: one item at a time, step by step. A wrong answer goes to the back of the step's
   queue and comes back until it is answered right; there is no penalty. Pure, so it is tested without a browser. */
export interface QueueState {
  step: number;            // index of the current step
  queue: string[];         // item ids still to clear in this step, the current one first
  cleared: number;         // items cleared in the whole lesson
}

export function startAt(steps: string[][], step = 0, itemId?: string): QueueState {
  const s = Math.min(Math.max(step, 0), steps.length - 1);
  const items = steps[s];
  const at = itemId ? items.indexOf(itemId) : -1;
  const cleared = steps.slice(0, s).reduce((n, st) => n + st.length, 0) + Math.max(at, 0);
  return { step: s, queue: at > 0 ? items.slice(at) : items.slice(), cleared };
}

/** The current item was cleared (explained, answered right, or skipped). */
export function clear(state: QueueState, steps: string[][]): QueueState {
  const queue = state.queue.slice(1);
  if (queue.length || state.step >= steps.length - 1) return { ...state, queue, cleared: state.cleared + 1 };
  return { step: state.step + 1, queue: steps[state.step + 1].slice(), cleared: state.cleared + 1 };
}

/** The current item was answered wrong: it comes back at the end of this step. */
export function retryLater(state: QueueState): QueueState {
  const [head, ...rest] = state.queue;
  return { ...state, queue: [...rest, head] };
}

export function finished(state: QueueState): boolean {
  return state.queue.length === 0;
}
