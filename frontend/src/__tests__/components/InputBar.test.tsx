import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InputBar } from "@/components/chat/InputBar";
import { useUiStore } from "@/stores/uiStore";

describe("InputBar", () => {
  const mockSend = vi.fn();

  beforeEach(() => {
    mockSend.mockClear();
    useUiStore.setState({ isStreaming: false, activeView: "chat", isConnected: false });
  });

  it("renders textarea and send button", () => {
    render(<InputBar onSend={mockSend} />);
    expect(screen.getByPlaceholderText(/Ask about music/)).toBeInTheDocument();
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("sends message on button click", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    const textarea = screen.getByPlaceholderText(/Ask about music/);
    await user.type(textarea, "hello");
    await user.click(screen.getByLabelText("Send message"));

    expect(mockSend).toHaveBeenCalledWith("hello");
  });

  it("sends message on Ctrl+Enter", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    const textarea = screen.getByPlaceholderText(/Ask about music/);
    await user.type(textarea, "hello");
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(mockSend).toHaveBeenCalledWith("hello");
  });

  it("does not send empty message", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    await user.click(screen.getByLabelText("Send message"));
    expect(mockSend).not.toHaveBeenCalled();
  });

  it("disables input when streaming", () => {
    useUiStore.setState({ isStreaming: true, activeView: "chat", isConnected: false });
    render(<InputBar onSend={mockSend} />);

    expect(screen.getByPlaceholderText(/Ask about music/)).toBeDisabled();
  });
});
