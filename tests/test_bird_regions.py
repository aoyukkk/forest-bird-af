import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from bird_parts_regions import context_region, automatic_regions, map_predictions, tiles,combine_native_boxes_and_eyes


class RegionTests(unittest.TestCase):
    def test_edge_region_retains_aspect_and_extent(self):
        x,y,r,b=context_region([370,245,384,256])
        self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
        self.assertLessEqual(r,384);self.assertLessEqual(b,256)
        self.assertAlmostEqual((r-x)/(b-y),1.5)
        self.assertGreaterEqual(r,384);self.assertGreaterEqual(b,256)

    def test_inverse_mapping_uses_offset_and_separate_scales(self):
        p=map_predictions([dict(kind='eye',point_xy=[192,128],score=.9)], [100,50,220,130])[0]
        self.assertEqual(p['point_xy'],[160,90])

    def test_auto_regions_do_not_require_oracle_or_missing_truth(self):
        self.assertEqual(automatic_regions([]),[])
        self.assertEqual(automatic_regions([dict(kind='eye',point_xy=[10,10],score=.99)]),[])
        self.assertEqual(len(automatic_regions([dict(kind='bird',box_xyxy=[10,10,40,40],score=.8)])),1)

    def test_tiles_cover_all_corners(self):
        for x,y in [(0,0),(384,0),(0,256),(384,256)]:
            self.assertTrue(any(a<=x<=c and b<=y<=d for a,b,c,d in tiles()))

    def test_hybrid_preserves_overlapping_native_packets(self):
        boxes=[dict(kind='bird',box_xyxy=[10,10,50,50],score=.9),
               dict(kind='bird',box_xyxy=[11,11,49,49],score=.8)]
        eyes=[dict(kind='eye',point_xy=[20,20],score=.9),dict(kind='eye',point_xy=[21,21],score=.8)]
        combined=combine_native_boxes_and_eyes(boxes,eyes)
        self.assertEqual(combined[:2],boxes)
        self.assertEqual(len(combined),3)
