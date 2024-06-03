from dataclasses import dataclass
from enum import Enum
from fractions import Fraction


class LengthUnit(Enum):
    rmpts = "ReMarkable points"
    mupts = "PyMuPDF points"
    mm = "Millimeter"


@dataclass
class Dimensions:
    width: int
    height: int
    unit: LengthUnit

    @property
    def aspect_ratio_for_humans(self) -> Fraction:
        aspect_ratio = Fraction(self.width, self.height)
        return aspect_ratio.limit_denominator()

    @property
    def aspect_ratio_for_calculations(self) -> float:
        return self.width / self.height


@dataclass()
class ReMarkableDimensions(Dimensions):
    unit: LengthUnit = LengthUnit.rmpts

    def to_mm(self):
        return PaperDimensions(int(self.width * (2100/1404)), int(self.height * (2970 / 1872)))


@dataclass
class PaperDimensions(Dimensions):
    """Dimensions in mm for paper, useful to specify standardized sizes like A4"""
    unit: LengthUnit = LengthUnit.mm

    def to_mu(self):
        return PyMuPDFDimensions(int(self.width * (210 / 595)), int(self.height * (210 / 595)))


@dataclass
class PyMuPDFDimensions(Dimensions):
    """The internal values used in PyMuPdf to specify a pdf size"""
    unit: LengthUnit = LengthUnit.mupts

    def to_mm(self):
        return PaperDimensions(int(self.width * (210 / 595)), int(self.height * (210 / 595)))


# PyMuPDF's A4 default is width=595, height=842


a4_dimensions = PaperDimensions(width=210, height=297)
REMARKABLE_PHYSICAL_SCREEN = PaperDimensions(width=188, height=246)
REMARKABLE_DOCUMENT = ReMarkableDimensions(width=1404, height=1872)
mu_a4 = PyMuPDFDimensions(width=595, height=842)
