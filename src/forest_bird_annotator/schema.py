"""Machine-readable annotation vocabulary and editable instance templates."""
def instance_template():
    return {'instance_id':'b1','bird_bbox_xyxy':None,'head_bbox_xyxy':None,'eyes':[],
        'part_visibility':{'bird':'unknown','head':'unknown','eye':'unknown'},
        'invisibility_reasons':[],'occluder_types':[],'occluded_parts':[],
        'target_mode':'auto','anchor_mode':'manual','af_reference_target_input':'unknown',
        'af_anchor_input_xy':None,'needs_review':False,'notes':'','next_eye_id':1}


def describe():
    return {'schema_version':'forest-bird-input-manual-v1',
        'coordinate_space':{'width':384,'height':256,'boxes':'xyxy; exclusive bottom-right',
                            'points':'0 <= x < 384; 0 <= y < 256'},
        'instance_template':instance_template(),
        'eye_template':{'eye_id':'e1','center_xy':[0,0],'bbox_xyxy':None,'side':'unknown'},
        'uncertain_region_template':{'region_id':'u1','bbox_xyxy':[0,0,1,1],'reason':'unknown','needs_review':True},
        'statuses':['pending','draft','annotated','reviewed','needs_adjudication'],
        'presence':[None,'present','absent','uncertain'],
        'visibility':['visible','partial','hidden','out_of_frame','unknown'],
        'targets':['eye','head','body','none','unknown'],
        'occluder_types':['none','branch','leaf','dense_foliage','trunk','grass','other_bird','other','unknown'],
        'occluded_parts':['bird','head','eye'],
        'invisibility_reasons':['occlusion','pose','defocus','motion_blur','too_small','compression','out_of_frame','unknown'],
        'rules':['Templates are unlabelled examples, not ground truth.',
          'Fetch /api/annotations/{id} for the frozen image identity before editing.',
          'Include every visible bird and all locatable head/eye parts, with stable per-image IDs.',
          'Use draft for work in progress. For annotated status inspect the whole image and supply arrays and presence.',
          'Keep geometry null for hidden/unlocatable parts. Do not infer eyes from the original reference.',
          'A target of eye/head/body requires corresponding geometry and an actual visible focus anchor.',
          'body means the whole visible bird, not a newly defined torso class.',
          'Use side=unknown if anatomical left/right is uncertain.',
          'Do not recycle deleted instance IDs or reset id_counters.',
          'reference_consulted records reference use; labels remain input-scale evidence.',
          'Raw model slots, including slot 5 auxiliary regions, are never automatic semantic annotations.',
          'AI writes use actor.kind=ai and cannot set reviewed.']}
