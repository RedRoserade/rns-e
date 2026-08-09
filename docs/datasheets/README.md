# Datasheets

Vendor datasheets are copyright their respective manufacturers and are **not
redistributed in this repository**. This directory is gitignored apart from this
file — drop your own local copies here and the tooling and docs will find them
at the paths below.

| file            | part       | manufacturer                      | where to get it |
| --------------- | ---------- | --------------------------------- | --------------- |
| `MB90561A.pdf`  | MB90561A   | Fujitsu (now Infineon, via Cypress) | [datasheet4u.com/pdf/629702/MB90561A.pdf](https://datasheet4u.com/pdf/629702/MB90561A.pdf) |

The MB90561A is the 16-bit microcontroller on the RNS-E front panel's control
board. It is a long-discontinued part and Fujitsu's original semiconductor
business has since passed to Infineon by way of Cypress, so the canonical
download has moved around; the link above is a third-party mirror. If it rots,
search for the exact part number — `MB90561A`, of the MB90560 series — rather
than for a URL.

Nothing in this repository requires the datasheet to run. It is referenced only
to explain *why* the hardware behaves as it does (pin functions, the reset
pull-up range, the PPG1 timer output).
