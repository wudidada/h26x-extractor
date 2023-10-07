import unittest

from h26x_extractor.macroblock import *


class MacroblockTest(unittest.TestCase):
    def test_MbPartPredMode(self):
        # B_L0_L0_16x8 2 Pred_L0 Pred_L0 16 8
        block = MacroBlock()
        block.mb_type = B_L0_L0_16x8
        block.slice_type = "B"
        self.assertEqual(block.MbPartPredMode(0), Pred_L0)
        self.assertEqual(block.MbPartPredMode(1), Pred_L0)

        # P_L0_L0_16x8 2 Pred_L0 Pred_L0 16 8
        block = MacroBlock(slice_type='P', real_mb_type=P_L0_L0_16x8)
        self.assertEqual(block.MbPartPredMode(0), Pred_L0)
        self.assertEqual(block.MbPartPredMode(1), Pred_L0)

        # I_16x16_0_0_0 na Intra_16x16 0 0 0
        block = MacroBlock(slice_type='I', real_mb_type=I_16x16_0_0_0)
        self.assertEqual(block.MbPartPredMode(0), Intra_16x16)

    def test_NumMbPart(self):
        # B_L0_L0_16x8 2 Pred_L0 Pred_L0 16 8
        block = MacroBlock()
        block.mb_type = B_L0_L0_16x8
        block.slice_type = "B"
        self.assertEqual(block.NumMbPart(), 2)

        # P_L0_L0_16x8 2 Pred_L0 Pred_L0 16 8
        block = MacroBlock(slice_type='P', real_mb_type=P_L0_L0_16x8)
        self.assertEqual(block.NumMbPart(), 2)

    def test_SubMbPredMode(self):
        # 1 P_L0_8x4 2 Pred_L0 8 4
        block = MacroBlock(slice_type='P', real_mb_type=P_L0_8x4)
        self.assertEqual(block.SubMbPredMode(1), Pred_L0)

        # 3 B_Bi_8x8 1 BiPred 8 8
        block = MacroBlock(slice_type='B', real_mb_type=B_Bi_8x8)
        self.assertEqual(block.SubMbPredMode(3), BiPred)

    def test_NumSubMbPart(self):
        # 1 P_L0_8x4 2 Pred_L0 8 4
        block = MacroBlock(slice_type='P', real_mb_type=P_L0_8x4)
        self.assertEqual(block.NumMbPart(1), 2)

        # 3 B_Bi_8x8 1 BiPred 8 8
        block = MacroBlock(slice_type='B', real_mb_type=B_Bi_8x8)
        self.assertEqual(block.NumMbPart(3), 1)