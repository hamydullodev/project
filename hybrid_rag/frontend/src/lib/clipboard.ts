/**
 * Copies `text` to the clipboard, returning whether it actually worked.
 *
 * WHY THIS EXISTS INSTEAD OF A BARE `navigator.clipboard.writeText()` CALL
 * -------------------------------------------------------------------------
 * `navigator.clipboard` can reject — denied permission, a non-secure
 * context, or a browser that never granted it in the first place (older
 * Safari, some embedded/automated contexts) — and an unhandled rejection
 * there means the caller's "Copied!" feedback silently never fires with
 * no error either, which is exactly what QA caught here. This tries the
 * modern API first, then falls back to the legacy `document.execCommand`
 * technique (a hidden, off-screen textarea) before giving up.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the legacy fallback below
  }

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    textarea.remove();
    return ok;
  } catch {
    return false;
  }
}
