
def assetRegistry(assetType):

    if assetType.lower() == "amortization":
        # * to avoid circular import, import module here *
        from AssetModeling.AmortizationAsset import AmortizationAsset
        return AmortizationAsset

    return None