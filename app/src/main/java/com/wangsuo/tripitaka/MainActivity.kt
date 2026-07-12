package com.wangsuo.tripitaka

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat

class MainActivity : Activity() {

    private lateinit var web: WebView
    private var pageReady = false
    private val inset = intArrayOf(0, 0, 0, 0) // top,right,bottom,left (dp/css-px)

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 沉浸式: WebView 铺满整窗; 系统栏尺寸注入成 CSS 变量, 由 web 自行避让
        WindowCompat.setDecorFitsSystemWindows(window, false)

        web = WebView(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(Color.parseColor("#efe4cb"))
            keepScreenOn = true
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                allowFileAccess = false
                allowContentAccess = false
                cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                textZoom = 100
            }
        }

        // 系统栏 + 刘海 inset -> CSS px, 注入 web
        ViewCompat.setOnApplyWindowInsetsListener(web) { _, insets ->
            val b = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            )
            val den = resources.displayMetrics.density
            inset[0] = (b.top / den).toInt()
            inset[1] = (b.right / den).toInt()
            inset[2] = (b.bottom / den).toInt()
            inset[3] = (b.left / den).toInt()
            pushSafe()
            insets
        }

        // 立即显示 WebView(纸色底), 库初始化(首启需拷 ~360M)放后台, 避免主线程 ANR
        setContentView(web)
        Thread {
            val store = SutraStore.open(this)
            runOnUiThread {
                val loader = WebViewAssetLoader.Builder()
                    .addPathHandler("/assets/", DataPathHandler(this, store))
                    .build()
                web.webViewClient = object : WebViewClientCompat() {
                    override fun shouldInterceptRequest(
                        view: WebView,
                        request: WebResourceRequest
                    ): WebResourceResponse? = loader.shouldInterceptRequest(request.url)

                    override fun onPageFinished(view: WebView, url: String) {
                        pageReady = true
                        pushSafe()
                    }
                }
                web.loadUrl("https://appassets.androidplatform.net/assets/index.html")
            }
        }.start()
    }

    private fun pushSafe() {
        if (!pageReady) return
        web.evaluateJavascript(
            "window.setSafe&&window.setSafe(${inset[0]},${inset[1]},${inset[2]},${inset[3]})",
            null
        )
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (this::web.isInitialized && web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        if (this::web.isInitialized) web.destroy()
        super.onDestroy()
    }
}
