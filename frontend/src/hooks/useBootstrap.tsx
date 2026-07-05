import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Bootstrap } from "@/lib/pywebview";

interface BootstrapContextValue {
  boot: Bootstrap;
  goalOrder: string[];
  // outputLanguageMap is {friendly label -> model value} - boot.config.output_language holds
  // the plain model value (e.g. "Japanese"), not the friendly label (e.g. "Japanese (日本語)"),
  // so this reverses the map. Falls back to the raw value for a custom/legacy value not in the map.
  outputLanguageLabel: () => string;
  applySavedSettings: (patch: {
    base_url: string;
    model: string;
    api_key: string;
    output_language: string;
    translateLanguage: string;
    autorun: boolean;
    selectedGoals: string[];
  }) => void;
}

const BootstrapContext = createContext<BootstrapContextValue | null>(null);

export function BootstrapProvider({ children }: { children: ReactNode }) {
  const [boot, setBoot] = useState<Bootstrap | null>(null);

  useEffect(() => {
    api()
      .get_bootstrap()
      .then(setBoot);
  }, []);

  const value = useMemo<BootstrapContextValue | null>(() => {
    if (!boot) return null;

    const outputLanguageLabel = () => {
      const label = Object.keys(boot.outputLanguageMap).find(
        (k) => boot.outputLanguageMap[k] === boot.config.output_language
      );
      return label || boot.config.output_language;
    };

    const applySavedSettings: BootstrapContextValue["applySavedSettings"] = (patch) => {
      setBoot((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          config: {
            ...prev.config,
            base_url: patch.base_url,
            model: patch.model,
            api_key: patch.api_key,
            output_language: patch.output_language,
          },
          translateLanguage: patch.translateLanguage,
          autorun: patch.autorun,
          selectedGoals: patch.selectedGoals,
        };
      });
    };

    return { boot, goalOrder: boot.goals.map((g) => g.value), outputLanguageLabel, applySavedSettings };
  }, [boot]);

  if (!value) return null;

  return <BootstrapContext.Provider value={value}>{children}</BootstrapContext.Provider>;
}

export function useBootstrap(): BootstrapContextValue {
  const ctx = useContext(BootstrapContext);
  if (!ctx) throw new Error("useBootstrap must be used within BootstrapProvider");
  return ctx;
}
