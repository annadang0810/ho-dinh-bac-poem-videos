# Chợ làng — The Village Market

Thơ: Hồ Đình Bắc · Giọng đọc: Hà Hồ

The poem has 14 lục bát lines, shown as three stanzas of four and a closing couplet.

- **Line 12:** the manuscript has "chảng chờ". It is shown as "chẳng chờ", read as a typing slip; the family has been asked to confirm.
- **Line 14:** "long đông" is kept exactly as written, since it rhymes with "đồng" in line 13.
- The manuscript page also carries the poet's contact details. They are never shown or stored.

## Lời thơ / Poem

| Tiếng Việt | English subtitle |
|---|---|
| Về quê đến với chợ làng | Back home, I wander to the village market |
| Người quen khách lạ vội vàng bán mua | Neighbours and strangers hurry to buy and sell |
| Dăm mớ cá mấy buộc cua | A few strings of fish, some bundles of crabs |
| Bắt từ đồng trũng ruộng chua mang về | Caught in the low, sour paddies and brought home |
| | |
| Tép gầy lấm chút bùn quê | Thin little shrimp, still muddy from the fields |
| Mớ rau bó lỏng vụng về thế thôi | Greens tied in loose, clumsy bunches, that is all |
| Không lều không quán vẫn ngồi | No stalls, no awnings, yet they sit |
| Bày hàng ra đất chào mời hồn nhiên | Laying wares on the ground, calling out with open hearts |
| | |
| Cứ mua dù chẳng mang tiền | Buy anyway, even without money |
| Người cùng xóm cả chả quên bao giờ | We are all one village, no one ever forgets |
| Chợ từ sáng sớm tinh mơ | The market starts in the first grey light of dawn |
| Dăm người cũng họp chẳng chờ chợ đông | A handful of people is enough, no need to wait for a crowd |
| | |
| Chưa tan đã vội ra đồng | Before it ends, they hurry off to the fields |
| Chợ quê bán cái long đông cả đời | The village market sells a lifetime of toil |

## Kịch bản ghi âm (chỉ giọng)

The intro is option 3 of three, chosen by Hà Hồ.

`/` = ngừng ngắn · `//` = ngừng lâu (khoảng 2 giây)

```
Mỗi lần về quê, điều tôi nhớ nhất là phiên chợ sớm dưới gốc đa đầu làng. /
Ở đó, quên mang tiền vẫn được mua, vì ai cũng là người cùng xóm. /
Tôi là Hà Hồ. Mời cả nhà cùng nghe bài thơ "Chợ làng" của bố tôi, nhà thơ Hồ Đình Bắc. //

Về quê đến với chợ làng /
Người quen khách lạ vội vàng bán mua /
Dăm mớ cá mấy buộc cua /
Bắt từ đồng trũng ruộng chua mang về //

Tép gầy lấm chút bùn quê /
Mớ rau bó lỏng vụng về thế thôi /
Không lều không quán vẫn ngồi /
Bày hàng ra đất chào mời hồn nhiên //

Cứ mua dù chẳng mang tiền /
Người cùng xóm cả chả quên bao giờ /
Chợ từ sáng sớm tinh mơ /
Dăm người cũng họp chẳng chờ chợ đông //

Chưa tan đã vội ra đồng /
Chợ quê bán cái long đông cả đời.
```

## Scene

The scene is the lifelike village from `mua-dong-thuong-me/`, rebuilt as the village entrance on market morning:

- An old banyan (cây đa đầu làng) with a wide canopy and hanging aerial roots. The village gate (cổng làng) has its name board and curled roof corners, and the bamboo hedge (lũy tre làng) shows roofs peeking over it. A beaten-earth market clearing lies where the lane meets the fields.
- **Light:** grey-blue dawn mist ("sáng sớm tinh mơ") hangs low over the fields and lifts as the sun rises, and the scene ends in a bright morning.
- **Sellers:** six market women in nón lá sit along the lane behind round trays (mẹt). Fish and crabs appear on "Dăm mớ cá mấy buộc cua", shrimp on "Tép gầy", and greens on "Mớ rau bó lỏng".
- **Buyers:** a neighbour comes out through the gate and stops at the stalls ("Người quen"), while a stranger walks up from the fields ("khách lạ").
- **Closing couplet:** "Chưa tan đã vội ra đồng". The sellers rise, shoulder their baskets on a carrying pole (đòn gánh) and walk off to the fields.

## Render

`timing.json` holds the line start times taken from Hà Hồ's recording. They were found with pause detection, and each line was checked against the lục bát rhythm: 6-syllable lines run about 2 s and 8-syllable lines about 3 s. The stanzas list 4, 4, 4 and 2 line times. The recording is not in the repo. It is trimmed to [0.6, 72.4] s and starts at video t = 0.8 s.

The spoken intro runs about 23 s, so the title card stays up for it and the two buyers start walking into the market during the intro.

```bash
python3 music.py music.wav sao
ffmpeg -i voice.m4a -af "atrim=0.6:72.4,asetpts=N/SR/TB,afade=t=in:d=0.2,highpass=f=80,afftdn=nf=-30,acompressor=threshold=-24dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,adelay=800:all=1,aresample=44100,aformat=channel_layouts=stereo" voice_clean.wav
for r in "0 20.6 p1" "20.6 41.2 p2" "41.2 61.8 p3" "61.8 82.4 p4"; do set -- $r; python3 silk.py full $1 $2 $3.mp4 & done; wait
printf "file '%s'\n" p1.mp4 p2.mp4 p3.mp4 p4.mp4 > list.txt
ffmpeg -f concat -i list.txt -i voice_clean.wav -i music.wav -filter_complex "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -movflags +faststart cho-lang.mp4
```
