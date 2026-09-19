import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; resetKey: string }
interface State { failed: boolean }

/** Keeps one broken page from blanking the whole app: shows a short message and a retry button instead. Resets when you navigate. */
export default class PageErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State { return { failed: true }; }

  componentDidUpdate(prev: Props) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }

  componentDidCatch(error: unknown) { console.error("Page crashed:", error); }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="mx-auto mt-16 max-w-lg rounded-3xl border border-border-soft bg-white/90 p-8 text-center shadow-sm">
        <h2 className="text-lg font-semibold text-strong">This page could not be shown</h2>
        <p className="mt-2 text-sm text-body">Something in the data was not what the page expected. The rest of the site is fine.</p>
        <button onClick={() => this.setState({ failed: false })} className="mt-5 rounded-lg bg-strong px-4 py-2 text-sm text-white">Try again</button>
      </div>
    );
  }
}
