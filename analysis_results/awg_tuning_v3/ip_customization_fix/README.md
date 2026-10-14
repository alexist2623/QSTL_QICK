# IP customization callback correction

The a3full2 startup failed before synthesis: the validator returned Tcl expr numeric 1 for DC_AREA_BITS=48. Returning the literal true/false strings corrected actual Vivado 2023.1 IP customization. A real catalog/BD probe accepted the default and explicit 48-bit setting, rejected 32 and 64 (expected ERROR messages inside catch), retained 48 and exited 0. This fixes only packaging; production RTL and the completed GUI/RTL source hashes remain unchanged.

Failed startup is retained at F:/Vivado_Output/a3full2. Full retry uses a3full3. No bitstream from either failed attempt is published.
