"""FootprintWizard to create a QR Code."""

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

# https://forum.kicad.info/t/qr-code-does-it-print-ok/13845/10
# https://github.com/s-light

# Originally by Stefan Krüger (s-light)
# Modified QRCode generator using Segno
# https://pypi.org/project/segno/

import pcbnew
import FootprintWizardBase
import segno


class QRCodeWizardSegno(FootprintWizardBase.FootprintWizard):
    """FootprintWizard to create a QR Code."""

    def __init__(self):
        self.allow_micro_qr = True
        self.border_auto = True
        self.border = 4
        self.content = 'Example'
        self.mask_cut_out = True
        self.negative = False
        self.qr_code = None
        self.pixel_size = 0.5
        self.symbol_size = None
        self.text_height = 1.2
        self.text_thickness = 0.12
        self.text_width = 1.2
        self.use_cu = True
        self.use_silk_s = False

    def GetName(self):
        """Return the name of the footprint wizard."""
        return '2D Barcode / QRCode (Segno)'

    def GetDescription(self):
        """Return the footprint wizard description."""
        return 'QR Code generator with extended options'

    def GetReferencePrefix(self):
        """Return the footprint reference designator prefix."""
        return 'QR***'

    def GetValue(self):
        """Return the value (name) of the generated footprint."""
        return self.module.Value().GetText()

    def GenerateParameterList(self):
        """Generate parameter list."""
        self.AddParam("Barcode", "Pixel Size", self.uMM, 0.5, min_value=0.01)
        self.AddParam("Barcode", "Border Auto", self.uBool, True)
        self.AddParam("Barcode", "Border", self.uInteger, 4)
        self.AddParam("Barcode", "Contents", self.uString, 'Example')
        self.AddParam("Barcode", "Allow Micro QR", self.uBool, True)
        self.AddParam("Barcode", "Negative", self.uBool, False)
        self.AddParam("Barcode", "Use SilkS layer", self.uBool, False)
        self.AddParam("Barcode", "Use Cu layer", self.uBool, True)
        self.AddParam("Barcode", "Mask CutOut", self.uBool, True)

        self.AddParam("Caption", "Height", self.uMM, 1.2)
        self.AddParam("Caption", "Width", self.uMM, 1.2)
        self.AddParam("Caption", "Thickness", self.uMM, 0.12)

    def CheckParameters(self):
        """Check parameters."""
        self.content = str(self.parameters['Barcode']['Contents'])
        self.pixel_size = self.parameters['Barcode']['Pixel Size']
        self.negative = self.parameters['Barcode']['Negative']
        self.use_silk_s = self.parameters['Barcode']['Use SilkS layer']
        self.use_cu = self.parameters['Barcode']['Use Cu layer']
        self.mask_cut_out = self.parameters['Barcode']['Mask CutOut']

        self.border_auto = self.parameters['Barcode']['Border Auto']
        self.border = int(self.parameters['Barcode']['Border'])
        self.allow_micro_qr = self.parameters['Barcode']['Allow Micro QR']

        self.text_height = int(self.parameters['Caption']['Height'])
        self.text_thickness = int(self.parameters['Caption']['Thickness'])
        self.text_width = int(self.parameters['Caption']['Width'])
        self.module.Value().SetText(str(self.content))

        # Build Qrcode
        self.qr_code = segno.make(str(self.content), micro=self.allow_micro_qr)

        if self.border_auto:
            self.parameters['Barcode']['Border'] = self.qr_code.default_border_size
            # None means automatic border width
            self.border = None

        self.symbol_size = self.qr_code.symbol_size(border=self.border)

    def __draw_square_area(
      self,
      layer,
      size,
      x_position,
      y_position,
      line_width=0
      ):
        """Draw square area."""
        # prepare values
        # 0,000005mm == 5
        line_width = int(line_width * 1000)
        x_position = int(x_position)
        y_position = int(y_position)

        # creates a filled FP_SHAPE of polygon type. The polygon is a square
        polygon = pcbnew.FP_SHAPE(self.module)
        polygon.SetShape(pcbnew.SHAPE_T_POLY)
        polygon.SetWidth(line_width)
        polygon.SetLayer(layer)
        halfsize = int(size / 2)
        polygon.GetPolyShape().NewOutline()
        polygon.GetPolyShape().Append(halfsize + x_position, halfsize + y_position)
        polygon.GetPolyShape().Append(halfsize + x_position, -halfsize + y_position)
        polygon.GetPolyShape().Append(-halfsize + x_position, -halfsize + y_position)
        polygon.GetPolyShape().Append(-halfsize + x_position, halfsize + y_position)
        polygon.SetFilled(True)
        return polygon

    def __draw_pixel(self, x_position, y_position):
        # build a square polygon on required layers
        if self.use_cu:
            polygon = self.__draw_square_area(
                pcbnew.F_Cu, self.pixel_size, x_position, y_position)
            self.module.Add(polygon)

        if self.use_silk_s:
            polygon = self.__draw_square_area(
                pcbnew.F_SilkS, self.pixel_size, x_position, y_position)
            self.module.Add(polygon)

    def __add_mask_cutout(self):
        pad = pcbnew.PAD(self.module)
        pad.SetSize(pcbnew.wxSize(
            self.pixel_size * self.symbol_size[0],
            self.pixel_size * self.symbol_size[1]))
        pad.SetPosition(pcbnew.wxPoint(0, 0))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetName("")
        layerset = pcbnew.LSET()
        layerset.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(layerset)
        self.module.Add(pad)

    def __draw_courtyard(self):
        """Draw Courtyard."""
        # https://klc.kicad.org/footprint/f5/f5.3/
        size = self.pixel_size * self.symbol_size[0]

        # add clearance
        size += pcbnew.FromMM(0.25 * 2)

        # Round courtyard positions to 0.1 mm,
        # rectangle will thus land on a 0.05mm grid
        pcbnew.PutOnGridMM(size, pcbnew.FromMM(0.10))

        # Draw Courtyard
        self.draw.SetLayer(pcbnew.F_CrtYd)
        self.draw.SetLineThickness(pcbnew.FromMM(0.05))
        self.draw.Box(0, 0, size, size)

    def BuildThisFootprint(self):
        """Build this Footprint."""
        # used many times...
        half_number_of_elements = self.symbol_size[0] / 2
        half_element_size = self.pixel_size/2

        # Center position of QrCode
        y_position = - int(half_number_of_elements * self.pixel_size - half_element_size)
        for line in self.qr_code.matrix_iter(border=self.border):
            x_position = - int(half_number_of_elements * self.pixel_size - half_element_size)
            for pixel in line:
                # Trust table for drawing a pixel
                # Negative is a boolean;
                # each pixel is a boolean (need to draw of not)
                # Negative | Pixel | Result
                #        0 |     0 | 0
                #        0 |     1 | 1
                #        1 |     0 | 1
                #        1 |     1 | 0
                # => Draw as Xor
                if self.negative != pixel:  # Xor...
                    self.__draw_pixel(x_position, y_position)
                x_position += self.pixel_size
            y_position += self.pixel_size

        # add mask cutout
        if self.use_cu and self.mask_cut_out:
            self.__add_mask_cutout()
        self.__draw_courtyard()

        # add labels
        # int((5 + half_number_of_elements) * self.pixel_size))
        text_position = int(
            (self.text_height) + ((1 + half_number_of_elements) * self.pixel_size))
        self.module.Value().SetPosition(pcbnew.wxPoint(0, - text_position))
        self.module.Value().SetTextHeight(self.text_height)
        self.module.Value().SetTextWidth(self.text_width)
        self.module.Value().SetTextThickness(self.text_thickness)
        self.module.Value().SetLayer(pcbnew.F_Fab)

        self.module.Reference().SetPosition(pcbnew.wxPoint(0, text_position))
        self.module.Reference().SetTextHeight(self.text_height)
        self.module.Reference().SetTextWidth(self.text_width)
        self.module.Reference().SetTextThickness(self.text_thickness)
        self.module.Reference().SetLayer(pcbnew.F_Fab)


QRCodeWizardSegno().register()
