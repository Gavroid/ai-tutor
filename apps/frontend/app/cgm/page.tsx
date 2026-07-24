"use client";

/**
 * Sprint 40: CGM opt-in page.
 *
 * T1D safety: user ВРУЧНУЮ вводит Nightscout URL. Opt-in.
 * Никаких medical recommendations.
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function CGMSettingsPage() {
  const [config, setConfig] = useState<{ nightscout_url: string; enabled: boolean } | null>(null);
  const [url, setUrl] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    api.isAuthenticated().then((auth) => {
      if (!auth) {
        window.location.href = "/login";
        return;
      }
      // Load current config
      fetch("/api/v1/cgm/config", { credentials: "include" })
        .then((r) => r.json())
        .then((data) => {
          setConfig(data);
          setUrl(data.nightscout_url || "");
          setEnabled(data.enabled || false);
        })
        .catch(() => setError("Не удалось загрузить настройки"));
    });
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);
    try {
      const r = await fetch("/api/v1/cgm/config", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nightscout_url: url, enabled }),
      });
      if (!r.ok) {
        const data = await r.json();
        throw new Error(data.detail || "Failed to save");
      }
      const data = await r.json();
      setConfig(data);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">
          CGM (Continuous Glucose Monitor)
        </h1>
        <p className="text-sm text-slate-600 mb-6">
          Sprint 40: опциональная интеграция с Nightscout (open-source CGM).
          <br />
          ⚠️ Не используется для медицинских решений. Только display.
        </p>

        <form
          onSubmit={handleSave}
          className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4"
        >
          <div>
            <label
              htmlFor="cgm-url"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              Nightscout URL
            </label>
            <input
              id="cgm-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://ns.example.com"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              data-testid="cgm-url-input"
            />
            <p className="text-xs text-slate-500 mt-1">
              Только HTTPS. Без localhost / 127.0.0.1 (SSRF protection).
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="cgm-enabled"
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="w-4 h-4"
              data-testid="cgm-enabled-checkbox"
            />
            <label htmlFor="cgm-enabled" className="text-sm text-slate-700">
              Показывать CGM badge (opt-in)
            </label>
          </div>

          {error && (
            <div
              role="alert"
              className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg p-3"
              data-testid="cgm-error"
            >
              {error}
            </div>
          )}

          {success && (
            <div
              role="status"
              className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg p-3"
              data-testid="cgm-success"
            >
              ✓ Настройки сохранены
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-sky-600 text-white rounded-lg px-4 py-2 font-medium hover:bg-sky-700 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
            data-testid="cgm-save-button"
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
        </form>

        <div className="mt-6 text-xs text-slate-500">
          <strong>Безопасность:</strong>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>URL не сохраняется в БД без вашего подтверждения</li>
            <li>Glucose values НЕ сохраняются в БД (только display)</li>
            <li>Отключите в любой момент (уберите галочку)</li>
          </ul>
        </div>

        <div className="mt-6">
          <a
            href="/"
            className="text-sky-600 hover:underline text-sm"
            data-testid="back-link"
          >
            ← На главную
          </a>
        </div>
      </div>
    </main>
  );
}
