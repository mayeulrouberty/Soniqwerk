import { RiChat1Fill, RiFileList3Fill, RiPlugFill, RiMusic2Fill } from "react-icons/ri";
import { cn } from "@/lib/utils";
import { useUiStore, type View } from "@/stores/uiStore";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItem {
  view: View;
  label: string;
  icon: React.ReactNode;
  locked?: boolean;
}

const navItems: NavItem[] = [
  { view: "chat", label: "Chat", icon: <RiChat1Fill size={22} /> },
  { view: "documents", label: "Documents", icon: <RiFileList3Fill size={22} /> },
  { view: "plugins", label: "Plugins (soon)", icon: <RiPlugFill size={22} />, locked: false },
  { view: "ableton", label: "Ableton (Phase 3)", icon: <RiMusic2Fill size={22} />, locked: true },
];

function VuMeter() {
  const isStreaming = useUiStore((s) => s.isStreaming);

  if (!isStreaming) return null;

  return (
    <div className="flex items-end gap-[3px] h-5 px-2 py-1">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="vu-bar w-[3px] rounded-full bg-green"
          style={{ height: "20%" }}
        />
      ))}
    </div>
  );
}

export function Sidebar() {
  const activeView = useUiStore((s) => s.activeView);
  const setActiveView = useUiStore((s) => s.setActiveView);

  return (
    <TooltipProvider delay={300}>
      <aside className="flex flex-col items-center w-16 bg-surface border-r border-border py-4 gap-2">
        {/* Logo */}
        <div className="text-accent font-display text-lg mb-4 select-none">SQ</div>

        {/* Nav items */}
        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map((item) => (
            <Tooltip key={item.view}>
              <TooltipTrigger
                onClick={() => !item.locked && setActiveView(item.view)}
                disabled={item.locked}
                className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-lg transition-colors",
                  activeView === item.view
                    ? "bg-accent/20 text-accent"
                    : "text-muted hover:text-text hover:bg-border/50",
                  item.locked && "opacity-30 cursor-not-allowed"
                )}
                aria-label={item.label}
              >
                {item.icon}
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>{item.label}</p>
              </TooltipContent>
            </Tooltip>
          ))}
        </nav>

        {/* VU meter */}
        <VuMeter />
      </aside>
    </TooltipProvider>
  );
}
