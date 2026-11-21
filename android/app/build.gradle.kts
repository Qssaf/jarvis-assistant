plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("app.cash.paparazzi")
}

android {
    namespace = "com.jarvis.assistant"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.jarvis.assistant"
        minSdk = 26
        targetSdk = 34
        versionCode = 5
        versionName = "2.5.0"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }  // (ONNX Runtime's libraries: phones only, half the size)
    }
    testOptions.unitTests.all { test ->  // WakeTest: where the wake word's models are (see its comment)
        System.getenv("WAKE_MODELS")?.let { test.environment("WAKE_MODELS", it) }
    }

    // release.yml's release build: signed with the keystore it names (made from the repository's secrets)
    System.getenv("ANDROID_KEYSTORE")?.let { keystore ->
        signingConfigs.create("release") {
            storeFile = file(keystore)
            storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyAlias = System.getenv("ANDROID_KEY_ALIAS")
            keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
        }
        buildTypes.getByName("release").signingConfig = signingConfigs.getByName("release")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.02.02"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.19.2")  // the wake word (Wake.kt)
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.19.2")  // (the same API with desktop libraries, for WakeTest)
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20231013")  // (the JVM tests need a real one: Android's is a stub there)
}

// Paparazzi's layoutlib needs the Guava it was built with (a newer one fails with IllegalAccessError in ResourceType)
configurations.matching { it.name.contains("UnitTest") }.configureEach {
    resolutionStrategy.force("com.google.guava:guava:31.1-jre")
}
