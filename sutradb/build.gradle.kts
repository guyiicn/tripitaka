plugins {
    id("com.android.asset-pack")
}

assetPack {
    packName.set("sutradb")
    dynamicDelivery {
        deliveryType.set("install-time")
    }
}
