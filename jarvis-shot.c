/* jarvis-shot: a screenshot of the whole desktop through KWin, ~10x faster than starting Spectacle.
 * KWin only lets programs listed in a .desktop file with X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2
 * take screenshots, by executable path, so this tiny program gets that permission instead of a whole interpreter.
 * Writes the raw image to stdout; the first line is "width height stride format" (format is a QImage::Format).
 * Build: gcc -O2 -o jarvis-shot jarvis-shot.c $(pkg-config --cflags --libs gio-unix-2.0) */
#include <gio/gio.h>
#include <gio/gunixfdlist.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    GError *err = NULL;
    GDBusConnection *bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &err);
    if (!bus) { fprintf(stderr, "%s\n", err->message); return 1; }
    int pipefd[2];
    if (pipe(pipefd)) { perror("pipe"); return 1; }
    GUnixFDList *fds = g_unix_fd_list_new_from_array(&pipefd[1], 1);  /* the list owns the write end now */
    GVariantBuilder opts;
    g_variant_builder_init(&opts, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&opts, "{sv}", "native-resolution", g_variant_new_boolean(TRUE));
    GVariant *res = g_dbus_connection_call_with_unix_fd_list_sync(
        bus, "org.kde.KWin", "/org/kde/KWin/ScreenShot2", "org.kde.KWin.ScreenShot2", "CaptureWorkspace",
        g_variant_new("(a{sv}h)", &opts, 0), G_VARIANT_TYPE("(a{sv})"), G_DBUS_CALL_FLAGS_NONE, 5000, fds, NULL, NULL, &err);
    g_object_unref(fds);  /* closes our copy of the write end, so the read below ends when KWin is done */
    if (!res) { fprintf(stderr, "%s\n", err->message); return 1; }
    GVariant *meta = g_variant_get_child_value(res, 0);
    guint32 w = 0, h = 0, stride = 0, format = 0;
    g_variant_lookup(meta, "width", "u", &w);
    g_variant_lookup(meta, "height", "u", &h);
    g_variant_lookup(meta, "stride", "u", &stride);
    g_variant_lookup(meta, "format", "u", &format);
    printf("%u %u %u %u\n", w, h, stride, format);
    fflush(stdout);
    char buf[1 << 16];
    ssize_t n;
    while ((n = read(pipefd[0], buf, sizeof buf)) > 0)
        fwrite(buf, 1, n, stdout);
    return 0;
}
