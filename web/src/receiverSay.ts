/**
 * Entry point for the bottom-right “Say anything” field.
 * Wire backend / WebSocket / transmit here later.
 */
export const receiverSay = {
  input: null as HTMLInputElement | null,

  init(el: HTMLInputElement): void {
    this.input = el;
  },

  get value(): string {
    return this.input?.value ?? "";
  },

  setValue(v: string): void {
    if (this.input) this.input.value = v;
  },

  focus(): void {
    this.input?.focus();
  },
};
