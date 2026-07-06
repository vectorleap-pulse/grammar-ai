import { useEffect, useState, type ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, type SettingsPayload } from "@/lib/pywebview";
import { useBootstrap } from "@/hooks/useBootstrap";
import { useAlertConfirm } from "@/hooks/useAlertConfirm";
import { statusColorClass } from "@/lib/status";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Mirrors app.js's Settings logic (app.js:455-574) + #settings-modal (index.html:100-156):
// open snapshots current values, Save/Test/Cancel, goal presets + checkboxes, restart-required
// confirm flow. Dialog state is initialized from bootstrap when opened.
export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const { boot, outputLanguageLabel, applySavedSettings } = useBootstrap();
  const { alert, confirm } = useAlertConfirm();

  const uiLabelForCode = () =>
    Object.keys(boot.uiLanguageMap).find((k) => boot.uiLanguageMap[k] === boot.uiLanguageCode) || "English";

  const [baseUrl, setBaseUrl] = useState(boot.config.base_url);
  const [model, setModel] = useState(boot.config.model);
  const [apiKey, setApiKey] = useState(boot.config.api_key);
  const [outputLanguage, setOutputLanguage] = useState(outputLanguageLabel());
  const [translateLanguage, setTranslateLanguage] = useState(boot.translateLanguage);
  const [uiLanguage, setUiLanguage] = useState(uiLabelForCode());
  const [autorun, setAutorun] = useState(boot.autorun);
  const [context, setContext] = useState(boot.config.context || "");
  const [goals, setGoals] = useState<string[]>(boot.selectedGoals);
  const [status, setStatus] = useState<{ text: string; color: string }>({ text: "", color: "gray" });
  const [testing, setTesting] = useState(false);

  // Re-snapshot current values each time the dialog opens (app.js's openSettings()).
  useEffect(() => {
    if (!open) return;
    setBaseUrl(boot.config.base_url);
    setModel(boot.config.model);
    setApiKey(boot.config.api_key);
    setOutputLanguage(outputLanguageLabel());
    setTranslateLanguage(boot.translateLanguage);
    setUiLanguage(uiLabelForCode());
    setAutorun(boot.autorun);
    setContext(boot.config.context || "");
    setGoals(boot.selectedGoals);
    setStatus({ text: "", color: "gray" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const collect = (): SettingsPayload => ({
    baseUrl,
    model,
    apiKey,
    outputLanguage,
    translateLanguage,
    uiLanguage,
    autorun,
    context,
    goals,
  });

  const toggleGoal = (value: string, checked: boolean) => {
    setGoals((prev) => (checked ? [...prev, value] : prev.filter((g) => g !== value)));
  };

  const onTest = async () => {
    setTesting(true);
    setStatus({ text: boot.strings.TESTING, color: "gray" });
    const res = await api().test_connection(collect());
    setStatus({ text: res.message, color: res.ok ? "green" : "red" });
    setTesting(false);
  };

  const onSave = async () => {
    const payload = collect();
    const res = await api().save_settings(payload);
    if (!res.ok) {
      void alert(res.error || boot.strings.ERROR);
      return;
    }
    applySavedSettings(payload);
    onOpenChange(false);
    if (
      res.restartRequired &&
      (await confirm(
        boot.strings.RESTART_TO_APPLY_LANGUAGE,
        boot.strings.RESTART_NOW,
        boot.strings.RESTART_LATER
      ))
    ) {
      void api().restart_app();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{boot.strings.SETTINGS}</DialogTitle>
        </DialogHeader>

        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto pr-1">
          <Field label={boot.strings.BASE_URL}>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </Field>
          <Field label={boot.strings.MODEL}>
            <Input value={model} onChange={(e) => setModel(e.target.value)} />
          </Field>
          <Field label={boot.strings.API_KEY}>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
          </Field>

          <Field label={boot.strings.POLISH_LANGUAGE}>
            <LanguageSelect
              value={outputLanguage}
              onChange={setOutputLanguage}
              options={boot.outputLanguages}
              title={boot.strings.OUTPUT_LANGUAGE_TOOLTIP}
            />
          </Field>
          <Field label={boot.strings.TRANSLATE_LANGUAGE}>
            <LanguageSelect
              value={translateLanguage}
              onChange={setTranslateLanguage}
              options={boot.outputLanguages}
            />
          </Field>
          <Field label={boot.strings.INTERFACE_LANGUAGE}>
            <LanguageSelect value={uiLanguage} onChange={setUiLanguage} options={boot.uiLanguages} />
          </Field>

          <label className="flex items-center gap-1.5 text-sm">
            <Checkbox checked={autorun} onCheckedChange={(c) => setAutorun(c === true)} />
            {boot.strings.RUN_AT_STARTUP}
          </label>

          <fieldset className="rounded-md border border-border p-2">
            <legend className="px-1 text-sm font-semibold text-muted-foreground">
              {boot.strings.GOALS_TO_GENERATE}
            </legend>
            <div className="mb-1.5 flex gap-1">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setGoals(boot.goalPresets.minimum)}
              >
                {boot.strings.MINIMUM}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setGoals(boot.goalPresets.default)}
              >
                {boot.strings.DEFAULT}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setGoals(boot.goalPresets.all)}
              >
                {boot.strings.ALL}
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {boot.goals.map((g) => (
                <label key={g.value} className="flex items-center gap-1 text-sm" title={g.description}>
                  <Checkbox
                    checked={goals.includes(g.value)}
                    onCheckedChange={(c) => toggleGoal(g.value, c === true)}
                  />
                  {g.label}
                </label>
              ))}
            </div>
            <p className="mt-1.5 text-sm italic text-muted-foreground">
              {boot.strings.MORE_GOALS_DISCLAIMER}
            </p>
          </fieldset>

          <Field label={boot.strings.CONTEXT}>
            <Textarea
              rows={3}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              title={boot.strings.CONTEXT_TOOLTIP}
            />
          </Field>

          <div className={`min-h-3.5 text-sm ${statusColorClass(status.color)}`}>{status.text}</div>
        </div>

        <div className="flex justify-end gap-1.5">
          <Button type="button" variant="outline" disabled={testing} onClick={onTest}>
            {boot.strings.TEST_CONNECTION}
          </Button>
          <Button type="button" onClick={onSave}>
            {boot.strings.SAVE}
          </Button>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            {boot.strings.CANCEL}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-semibold text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function LanguageSelect({
  value,
  onChange,
  options,
  title,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  title?: string;
}) {
  return (
    <Select value={value} onValueChange={(v) => v !== null && onChange(v)}>
      <SelectTrigger className="w-full" title={title}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((label) => (
          <SelectItem key={label} value={label}>
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
