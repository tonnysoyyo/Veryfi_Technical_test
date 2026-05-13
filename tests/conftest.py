import pytest


@pytest.fixture
def switch_ocr_text():
    return """
Switch
PO Box 674592
Dallas, TX 75267-4592

Invoice Date Due Date Invoice No.
09/22/23 08/27/24 1556267

Toni Hackel
123 Main Street
Las Vegas, NV 89101

Account No. P.O. Number Services for month of
123456 PO-789 September 2023

Description Quantity Rate Amount
Transport | Switch Fiber Pair (Intra-campus) | Pairs (4419693704) (04/2023|10 Gbps Fiber
to HOEpyb (YSPG4VFH) (04/2023) 2912.98 934.09 2720985.49
Carrier Taxes for Transport | 230 Gbps Wavelength Diverse between Sparks, OR 56789 and
Plano, NV 98765 (SNpTfT) (NJYM5MQP) (07/2023 Taxes) (07/2023) 3500.87 6229.33 21808074.52
Special Partnership Discount (03/2023) 8.00 -561.00 -4488.00
Item Discount: Special Partnership Discount (11/2023) 8.00 -296.00 -2368.00

Total USD $58,164,641.64
Please update your system with our new remittance instruction located on this invoice.
Please make payments to: Switch, Ltd.
Wire/ACH Payment: PNC Bank, N.A.
www.switch.com
"""


@pytest.fixture
def unsupported_text():
    return """
Certificate of Completion

This document certifies that a student completed a training course.
It is not an invoice.
It does not contain a Switch invoice table.
"""