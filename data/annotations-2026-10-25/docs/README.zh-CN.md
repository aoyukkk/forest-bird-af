# 宸叉爣娉ㄧ粨鏋滐紙2026-10-25 蹇収锛?

[English](README.md) | **绠€浣撲腑鏂?*

鏈洰褰曞彂甯?**Z8 杈呭姪浜哄伐绾犻敊鏍囩** 鍜?**鍐荤粨璇勪及鍒掑垎**锛屼笉鍚浘鐗囥€佸師濮嬭祫浜у搱甯屻€?
鏁版嵁搴撴垨鏉冮噸銆傚浘鐗囨寜鎵规浠?Releases 鑾峰彇锛岀紪鍙峰鐓?[registry.csv](../../registry.csv)銆?

| 鏂囦欢 | 鍐呭 |
|---|---|
| [confirmed/](README.zh-CN.md) | **浜哄伐鏍″噯濂界殑鍏ㄩ儴 547 寮犳爣娉?*锛欽SONL銆丆SV銆丆OCO銆乊OLO 鍥涚鏍煎紡 |
| [labels/community-corrections-v1.jsonl](../labels/community-corrections-v1.jsonl) | 694 寮犲浘鐨勯€愬浘鏍囩锛圝SON Lines锛夛紝鍚?146 寮犳湭纭鑽夌 |
| [labels/community-corrections-v1.json](../labels/community-corrections-v1.json) | 璁℃暟銆佹爣绛炬枃浠跺搱甯屼笌瀛楁鍓旈櫎璇存槑 |
| [labels/summary.md](../labels/summary.md) | 涓€琛屽紡鎽樿 |
| [evaluation-split-v1.json](../splits/evaluation-split-v1.json) | 535 寮犺缁?楠岃瘉/娴嬭瘯鍒掑垎涓庡叧鑱旂粍 |
| [dedupe-queue-v1.json](../curation/dedupe-queue-v1.json) | 鍘婚噸闃熷垪锛?36 寮犲湪闃熷垪銆?58 寮犳姌鍙犮€?2 缁?|
| [best-images-v1.json](../curation/best-images-v1.json) | 120 寮犱紭鍏堝鏍告竻鍗曪紙鍙槸澶嶆牳椤哄簭寤鸿锛屼笉鏄爣绛鹃泦锛?|

鏂囨。锛?

| 鏂囦欢 | 鍐呭 |
|---|---|
| [TOOLCHAIN.zh-CN.md](TOOLCHAIN.zh-CN.md) | 鏍囨敞宸ュ叿閾撅細浠庡師鐗囧埌鍙缁冩爣绛剧殑鍏ㄦ祦绋嬩笌瀵煎嚭鏍煎紡 |
| [CURATION.zh-CN.md](CURATION.zh-CN.md) | 杈冨ソ鍥剧墖鎬庝箞閫夈€佸幓閲嶉槦鍒楃殑浜嬪疄 |
| [review-rounds.zh-CN.md](review-rounds.zh-CN.md) | 澶嶆牳杞銆佺籂閿欑粺璁′笌鍓╀綑闂 |

璁粌涓庡彂甯冭竟鐣岃[鍘熺敓妫€娴嬪ご寰皟](../../../docs/training/z8-native-head-finetune.zh-CN.md)涓嶽鏈彂甯冨唴瀹筣(../../../docs/releases/not-published.zh-CN.md)銆?

## 褰撳墠鐘舵€?

| 澶嶆牳鐘舵€?| 鍥炬暟 |
|---|---:|
| `confirmed`锛堜汉宸ョ‘璁わ級 | 547 |
| `draft`锛堟湭纭鑽夌锛?| 146 |
| `needs_adjudication`锛堝緟瑁佸喅锛?| 1 |

宸茬‘璁ょ殑 547 寮犲浘閲屽叡鏈?1,441 涓儴浣嶉」锛氶笩韬?566銆侀笩澶?412銆佺溂 223銆佽緟鍔╁尯鍩?240銆?
鍏朵腑 2 寮犳槸纭鏃犻笩鐨勭┖鍥俱€傚喕缁撳師鍘傚€欓€夊悎璁?1,495 涓紝瑕嗙洊 469 寮犲浘銆?

`draft` 琛屼繚鐣欐槸涓轰簡璁╁閮ㄨ鑰呯煡閬撳摢浜涘浘杩樻病澶嶆牳杩囷紝**涓嶈褰撲綔璐熸牱鏈?*銆?
Z8 鏈夊€欓€夎€屼汉宸ュ皻鏈‘璁ょ殑鍥撅紝鏃笉鏄€滅‘璁ゆ棤楦熲€濓紝涔熶笉鏄€滅‘璁ゆ湁璇€濄€?

## 瀛楁

姣忚鑷冲皯鍖呭惈锛?

```json
{
  "image_id": "fb_0001",
  "annotation_image": {
    "width": 384, "height": 256,
    "png_sha256": "...", "input_chw_u8_sha256": "...",
    "preprocess_id": "review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1",
    "coordinate_space": "z8_input_384x256"
  },
  "review_status": "confirmed",
  "presence": "present",
  "decision": "error",
  "revision": 5,
  "revisions": 5,
  "confirmed": true,
  "parts": {"bird": 1, "head": 0, "eye": 0},
  "items": [{"id": "n1", "kind": "bird", "box_xyxy": [163.0, 104.0, 224.5, 142.0]}],
  "frozen_z8_candidates": {"bird": 0, "head": 0, "eye": 0, "auxiliary": 0},
  "frozen_z8_candidate_total": 0,
  "frozen_baseline_matches_current": false,
  "diff": {"added": [], "removed": [], "changed": [], "unchanged": [], "changed_parts": ["bird"]},
  "review_changes": 1,
  "record_sha256": "..."
}
```

- `kind`锛歚bird`锛堟暣楦燂級銆乣head`锛堝惈鍠欑殑澶存锛夈€乣eye`锛堢溂涓績鐐癸級銆乣auxiliary`
  锛堝師鍘傞檮灞炲尯鍩燂紝**涓嶆槸**楦熻韩鐪熷€硷級銆傜溂鐗╁搧鍏?226 涓細160 涓甫涓績鐐?`point_xy`锛?
  66 涓彧鐢讳簡杈圭晫娓呮鐨勭溂妗?`box_xyxy`銆傜溂妗嗗楂樺彧鍦ㄨ竟鐣岀‘瀹炲彲瑙佹椂瀛樺湪锛屼笉鎵归噺
  缂栭€犲浐瀹氬儚绱犳銆?
- `decision`锛歚correct` 鍘熷巶姝ｇ‘銆乣partial_error` 閮ㄥ垎鏈夎銆乣error` 鏈夎銆?
  `uncertain` 涓嶇‘瀹氥€乣unassessed` 鏈垽瀹氥€?
- `diff` 淇濈暀閫愭澧炲垹鏀癸紱`frozen_z8_candidates` 鏄鏍稿墠鐨勫喕缁撳師鍘傚€欓€夎鏁般€?
- 鍧愭爣璇箟锛氫汉宸ユ涓?384脳256 杈撳叆涓婄殑鍗婂紑鍖洪棿 `xyxy`锛涘師鍘傚€欓€夋部鐢ㄥ師鏈哄惈绔偣鍍忕礌
  鍧愭爣锛屽洜姝や細鍑虹幇 `-0.5` 杩欑被鍊笺€備袱鑰呴兘鍦ㄥ悎娉曡寖鍥村唴銆?

## 鍒掑垎

| 鍒掑垎 | 鍥剧墖 | 淇濆畧鍏宠仈缁?| 楦?| 澶?| 鐪?|
|---|---:|---:|---:|---:|---:|
| train | 375 | 56 | 385 | 301 | 174 |
| val | 80 | 6 | 79 | 50 | 25 |
| test | 80 | 5 | 83 | 59 | 22 |

鍒掑垎鍦ㄨ缁冨墠鍐荤粨锛屽叧鑱旂粍涓嶈法鍒掑垎锛屾祴璇曢泦鍙湪楠岃瘉闆嗛€夊瀷鍚庢墦寮€涓€娆°€傚垎缁勪緷鎹姇绋?
瀛愮洰褰曘€佽瑙夌浉浼煎€欓€夊拰鍘婚噸鍏崇郴锛屾槸宸ョ▼闃叉硠婕忚繎浼硷紝涓嶇瓑浜庡凡鏍稿疄鐨勬媿鎽勪簨浠惰韩浠姐€?
80 寮犳祴璇曞浘閲屾湁 58 寮犲悓灞炰竴涓繚瀹堢粍銆?

## 鏍￠獙

```bash
python scripts/tools/verify_annotations.py
```

妫€鏌ラ」锛欽SON 瑙ｆ瀽銆佸潗鏍囪寖鍥淬€佺溂鐐瑰繀椤诲瓨鍦ㄣ€侀儴浣嶈鏁颁笌鏉＄洰涓€鑷淬€佺姸鎬佸彇鍊笺€佸垝鍒嗕笉璺ㄧ粍銆?
鍒掑垎璁℃暟涓€鑷达紝浠ュ強璺緞绫绘晱鎰熷瓧娈碉紙鍘熷浘缁濆璺緞銆佸師璧勪骇鍝堝笇绛夛級娌℃湁娉勬紡銆?

## 鍙仛浠€涔堛€佷笉鍙仛浠€涔?

鍙互锛氱绾胯瘎浼伴笩韬?楦熷ご/鐪兼娴嬶紝姣旇緝鍘熷巶妯″瀷涓庤嚜鐮旀敼鍔紝澶嶇幇鍙戝竷杩囩殑鍒掑垎銆?

涓嶅彲浠ワ細鎶婅繖浜涙暟瀛楄鎴愭満韬鐒︽垚鍔熺巼銆佺溂閿佹垚鍔熺巼鎴栭暅澶村悎鐒︽晥鏋滐紱鎶?
`draft` 褰撹礋鏍锋湰锛涙妸杈呭姪鍖哄煙褰撻笩韬爣绛撅紱鎶?Z8 杈呭姪澶嶆牳璇存垚鐙珛鐩叉爣銆?
