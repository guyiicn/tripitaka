package com.wangsuo.tripitaka

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.github.luben.zstd.Zstd
import com.github.luben.zstd.ZstdDictDecompress
import java.io.File

/**
 * 只读经藏库: SQLite + zstd(带训练词典) 压缩的 JSON blob。
 * 表: juan(id,jn,zb)  meta(id,zb)  kv(k,v)  [kv 内含 dict / catalog / schema]
 */
class SutraStore private constructor(
    private val db: SQLiteDatabase,
    private val dict: ZstdDictDecompress
) {
    private fun deco(zb: ByteArray): ByteArray {
        val size = Zstd.getFrameContentSize(zb)
        return Zstd.decompress(zb, dict, size.toInt())
    }

    private fun blob(sql: String, vararg args: String): ByteArray? {
        db.rawQuery(sql, args).use { c ->
            if (c.moveToFirst() && !c.isNull(0)) return c.getBlob(0)
        }
        return null
    }

    fun juan(id: String, jn: String): ByteArray? =
        blob("SELECT zb FROM juan WHERE id=? AND jn=? LIMIT 1", id, jn)?.let { deco(it) }

    fun meta(id: String): ByteArray? =
        blob("SELECT zb FROM meta WHERE id=? LIMIT 1", id)?.let { deco(it) }

    fun catalog(): ByteArray? =
        blob("SELECT v FROM kv WHERE k='catalog' LIMIT 1")?.let { deco(it) }

    companion object {
        private const val DB_ASSET = "db/tripitaka.db"
        private const val DB_NAME = "tripitaka.db"

        fun open(ctx: Context): SutraStore {
            val f = dbFile(ctx)
            val db = SQLiteDatabase.openDatabase(f.path, null, SQLiteDatabase.OPEN_READONLY)
            val dictBytes = rawKv(db, "dict") ?: ByteArray(0)
            return SutraStore(db, ZstdDictDecompress(dictBytes))
        }

        private fun rawKv(db: SQLiteDatabase, k: String): ByteArray? {
            db.rawQuery("SELECT v FROM kv WHERE k=? LIMIT 1", arrayOf(k)).use { c ->
                if (c.moveToFirst() && !c.isNull(0)) return c.getBlob(0)
            }
            return null
        }

        /** release: Play Asset Delivery install-time 资产包内直接读库(免拷贝); debug: 从 app assets 拷到内部存储。 */
        private fun dbFile(ctx: Context): File {
            packDbPath(ctx)?.let { p ->
                val f = File(p)
                if (f.exists() && f.length() > 0) return f
            }
            return ensureFromAssets(ctx)
        }

        private fun packDbPath(ctx: Context): String? = try {
            val loc = com.google.android.play.core.assetpacks.AssetPackManagerFactory
                .getInstance(ctx).getPackLocation("sutradb")
            loc?.assetsPath()?.let { "$it/db/tripitaka.db" }
        } catch (t: Throwable) {
            null
        }

        private fun ensureFromAssets(ctx: Context): File {
            val out = File(ctx.filesDir, DB_NAME)
            val am = ctx.assets
            val expect = try { am.openFd(DB_ASSET).use { it.length } } catch (e: Exception) { -1L }
            if (out.exists() && expect > 0 && out.length() == expect) return out
            am.open(DB_ASSET).use { input ->
                out.outputStream().use { output -> input.copyTo(output, 1 shl 20) }
            }
            return out
        }
    }
}
