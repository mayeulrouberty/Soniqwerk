import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { DocumentLibrary } from "@/components/documents/DocumentLibrary";
import { useUiStore } from "@/stores/uiStore";

function PluginsPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="font-display text-3xl text-accent mb-2">Plugins</h2>
        <p className="text-muted text-sm">Plugin management coming soon.</p>
      </div>
    </div>
  );
}

function AbletonPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-sm">
        <h2 className="font-display text-3xl text-accent mb-3">Ableton Live</h2>
        <p className="text-muted text-sm mb-4">
          Connect the Max for Live device to control your session via AI.
        </p>
        <p className="text-xs text-muted/60 font-mono">
          See <span className="text-accent/80">ableton/README.md</span> for setup instructions.
        </p>
      </div>
    </div>
  );
}

function MainContent() {
  const activeView = useUiStore((s) => s.activeView);

  switch (activeView) {
    case "chat":
      return <ChatWindow />;
    case "documents":
      return <DocumentLibrary />;
    case "plugins":
      return <PluginsPlaceholder />;
    case "ableton":
      return <AbletonPlaceholder />;
    default:
      return <ChatWindow />;
  }
}

function App() {
  return (
    <div className="flex h-screen bg-bg overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <MainContent />
        </main>
      </div>
    </div>
  );
}

export default App;
