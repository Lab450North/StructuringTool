def structureRegistry(structureType):

    if structureType.lower() == "termabs":
        # * to avoid circular import, import module here *
        from StructureModeling.TermABS import TermABS
        return TermABS

    elif structureType.lower() == "warehouse":
        from StructureModeling.Warehouse import Warehouse
        return Warehouse

    return None