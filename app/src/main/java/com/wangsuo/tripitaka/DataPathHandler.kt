package com.wangsuo.tripitaka

import android.content.Context
import android.webkit.WebResourceResponse
import androidx.webkit.WebViewAssetLoader
import java.io.ByteArrayInputStream

/**
 * 挂在 /assets/ 下, 统一处理:
 *   data/<id>/<jn>.json  -> SQLite juan/meta
 *   catalog.json         -> SQLite kv.catalog
 *   其它(html/js/css/font)-> assets/web/<path>
 */
class DataPathHandler(
    ctx: Context,
    private val store: SutraStore
) : WebViewAssetLoader.PathHandler {

    private val am = ctx.assets

    override fun handle(path: String): WebResourceResponse? {
        return try {
            when {
                path.startsWith("data/") -> {
                    val rest = path.removePrefix("data/").removeSuffix(".json")
                    val slash = rest.indexOf('/')
                    if (slash <= 0) return notFound()
                    val id = rest.substring(0, slash)
                    val jn = rest.substring(slash + 1)
                    val bytes = if (jn == "_meta") store.meta(id) else store.juan(id, jn)
                    if (bytes == null) notFound() else json(bytes)
                }
                path == "catalog.json" -> {
                    val b = store.catalog()
                    if (b == null) notFound() else json(b)
                }
                else -> {
                    val mime = mimeOf(path)
                    resp(mime, am.open("web/$path"))
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun json(b: ByteArray) =
        resp("application/json", ByteArrayInputStream(b))

    private fun notFound() =
        WebResourceResponse("text/plain", "utf-8", 404, "Not Found", noStore(), ByteArrayInputStream(ByteArray(0)))

    private fun resp(mime: String, stream: java.io.InputStream) =
        WebResourceResponse(mime, if (mime.startsWith("text") || mime.endsWith("json")) "utf-8" else null, 200, "OK", noStore(), stream)

    private fun noStore() = hashMapOf("Cache-Control" to "no-store")

    private fun mimeOf(p: String): String = when {
        p.endsWith(".html") -> "text/html"
        p.endsWith(".js") -> "text/javascript"
        p.endsWith(".css") -> "text/css"
        p.endsWith(".json") -> "application/json"
        p.endsWith(".woff2") -> "font/woff2"
        p.endsWith(".woff") -> "font/woff"
        p.endsWith(".ttf") -> "font/ttf"
        p.endsWith(".png") -> "image/png"
        p.endsWith(".svg") -> "image/svg+xml"
        else -> "application/octet-stream"
    }
}
