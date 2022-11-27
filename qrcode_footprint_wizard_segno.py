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

    GetName = lambda self: '2D Barcode / QRCode (Segno)'
    GetDescription = lambda self: 'QR Code generator with extended options'
    GetReferencePrefix = lambda self: 'QR***'
    GetValue = lambda self: self.module.Value().GetText()

    def GenerateParameterList(self):
        """Generate parameter list."""
        self.AddParam("Barcode", "Pixel Width", self.uMM, 0.5, min_value=0.01)
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
        """Check parameter."""
        self.Barcode = str(self.parameters['Barcode']['Contents'])
        self.X = self.parameters['Barcode']['Pixel Width']
        self.negative = self.parameters['Barcode']['Negative']
        self.UseSilkS = self.parameters['Barcode']['Use SilkS layer']
        self.UseCu = self.parameters['Barcode']['Use Cu layer']
        self.MaskCutOut = self.parameters['Barcode']['Mask CutOut']

        self.border_auto = self.parameters['Barcode']['Border Auto']
        self.border = int(self.parameters['Barcode']['Border'])
        self.allow_micro_qr = self.parameters['Barcode']['Allow Micro QR']

        self.textHeight = int(self.parameters['Caption']['Height'])
        self.textThickness = int(self.parameters['Caption']['Thickness'])
        self.textWidth = int(self.parameters['Caption']['Width'])
        self.module.Value().SetText(str(self.Barcode))

        # Build Qrcode
        # use all default options
        if self.allow_micro_qr:
            self.qr = segno.make(str(self.Barcode))
        else:
            self.qr = segno.make_qr(str(self.Barcode))

        if self.border_auto:
            self.parameters['Barcode']['Border'] = self.qr.default_border_size
            # None means automatic border width
            self.border = None

        self.symbol_size = self.qr.symbol_size(border=self.border)

    def drawSquareArea(self, layer, size, xposition, yposition, line_width=0):
        """Draw square area."""
        # prepare values
        # 0,000005mm == 5
        line_width = int(line_width * 1000)
        xposition = int(xposition)
        yposition = int(yposition)
        # creates a filled FP_SHAPE of polygon type. The polygon is a square
        # this could possibly be replaced with
        polygon = pcbnew.FP_SHAPE(self.module)
        polygon.SetShape(pcbnew.SHAPE_T_POLY)
        polygon.SetWidth(line_width)
        polygon.SetLayer(layer)
        halfsize = int(size / 2)
        polygon.GetPolyShape().NewOutline()
        polygon.GetPolyShape().Append(
            halfsize + xposition, halfsize + yposition)
        polygon.GetPolyShape().Append(
            halfsize + xposition, -halfsize + yposition)
        polygon.GetPolyShape().Append(
            - halfsize + xposition, -halfsize + yposition)
        polygon.GetPolyShape().Append(
            - halfsize + xposition, halfsize + yposition)
        polygon.SetFilled(True)
        return polygon

    def _drawPixel(self, xposition, yposition):
        # build a rectangular pad as a dot on copper layer,
        # and a polygon (a square) on silkscreen
        if self.UseCu:
            pad = pcbnew.PAD(self.module)
            pad.SetSize(pcbnew.wxSize(self.X, self.X))
            pad.SetPosition(pcbnew.wxPoint(xposition, yposition))
            pad.SetShape(pcbnew.PAD_SHAPE_RECT)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetName("")
            layerset = pcbnew.LSET()
            layerset.AddLayer(pcbnew.F_Cu)
            if not self.MaskCutOut:
                layerset.AddLayer(pcbnew.F_Mask)
            pad.SetLayerSet(layerset)
            self.module.Add(pad)
        if self.UseSilkS:
            polygon = self.drawSquareArea(
                pcbnew.F_SilkS, self.X, xposition, yposition)
            self.module.Add(polygon)

    def _add_MaskCutOut(self):
        pad = pcbnew.PAD(self.module)
        pad.SetSize(pcbnew.wxSize(
            self.X * self.symbol_size[0],
            self.X * self.symbol_size[1]))
        pad.SetPosition(pcbnew.wxPoint(0, 0))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetName("")
        layerset = pcbnew.LSET()
        layerset.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(layerset)
        self.module.Add(pad)

    def _draw_coutyard(self):
        """Draw Courtyard."""
        # https://klc.kicad.org/footprint/f5/f5.3/
        size = self.X * self.symbol_size[0]
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

        # Center position of QrCode
        yposition = - int(half_number_of_elements * self.X)
        for line in self.qr.matrix_iter(border=self.border):
            xposition = - int(half_number_of_elements * self.X)
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
                    self._drawPixel(xposition, yposition)
                xposition += self.X
            yposition += self.X
        # add mask cutout
        if self.UseCu and self.MaskCutOut:
            self._add_MaskCutOut()
        self._draw_coutyard()
        # add labels
        # int((5 + half_number_of_elements) * self.X))
        textPosition = int(
            (self.textHeight) + ((1 + half_number_of_elements) * self.X))
        self.module.Value().SetPosition(pcbnew.wxPoint(0, - textPosition))
        self.module.Value().SetTextHeight(self.textHeight)
        self.module.Value().SetTextWidth(self.textWidth)
        self.module.Value().SetTextThickness(self.textThickness)
        self.module.Value().SetLayer(pcbnew.F_Fab)
        
        self.module.Reference().SetPosition(pcbnew.wxPoint(0, textPosition))
        self.module.Reference().SetTextHeight(self.textHeight)
        self.module.Reference().SetTextWidth(self.textWidth)
        self.module.Reference().SetTextThickness(self.textThickness)
        self.module.Reference().SetLayer(pcbnew.F_Fab)

QRCodeWizardSegno().register()
