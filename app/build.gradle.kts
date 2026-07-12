import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// 签名配置 (keystore.properties 不入 git; 无此文件时 release 不签名, 用于纯构建校验)
val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) load(FileInputStream(keystorePropsFile))
}
val hasSigning = keystoreProps.getProperty("storeFile") != null

android {
    namespace = "com.wangsuo.tripitaka"
    compileSdk = 34

    // Play Asset Delivery: 经藏库走 install-time 资产包
    assetPacks += listOf(":sutradb")

    defaultConfig {
        applicationId = "com.wangsuo.tripitaka"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        vectorDrawables { useSupportLibrary = true }
    }

    signingConfigs {
        create("release") {
            if (hasSigning) {
                storeFile = file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (hasSigning) signingConfig = signingConfigs.getByName("release")
        }
        debug {
            applicationIdSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    // 数据库资产不压缩 (debug 首启拷贝 / 资产包直接打开)
    androidResources { noCompress += "db" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.webkit:webkit:1.10.0")
    implementation("com.github.luben:zstd-jni:1.5.6-3@aar")
    implementation("com.google.android.play:asset-delivery:2.2.0")
}
