# Thăm lại chùa xưa — Revisiting the Old Pagoda

Thơ: Hồ Đình Bắc · Giọng đọc: Hà Hồ

The poem has 16 lục bát lines, shown as four stanzas of four. The spaced hyphen in "Khói hương chùa vắng - tình đầu ai quên?" is kept as the poet wrote it. The manuscript's place line is not shown in the video.

## Lời thơ / Poem (transcribed exactly from the manuscript)

| Tiếng Việt | English subtitle |
|---|---|
| Eo thon mặc áo nâu sồng | Your slender waist now wrapped in a brown robe |
| Khăn chùa thay mái tóc bồng ngày xưa | A temple scarf where your full hair once flowed |
| Để giờ mõ sớm, kinh trưa | Now the wooden bell at dawn, sutras at noon |
| Mắt buồn xuân cũ như vừa ướt mi. | Sad eyes of a spring long past, lashes still wet. |
| | |
| Thinh không chùa vắng từ bi | In the silent, empty temple of compassion |
| Quên sao ngày ấy em đi lễ chùa | How could I forget the day you came to pray |
| Tóc dài vương những sợi mưa | Your long hair caught with threads of rain |
| Cầu duyên khi tuổi mới vừa sang xuân. | Praying for love, just stepping into your spring. |
| | |
| Không ngờ duyên nợ phong trần | Who knew that fate would bring such hardship |
| Tình tan như nắng qua sân dãi dầu | Love faded like sunlight crossing a weathered yard |
| Còn đâu duyên lễ, duyên cầu | Gone the vows, gone the prayers for love |
| Khói hương chùa vắng - tình đầu ai quên? | Incense in an empty temple - who forgets first love? |
| | |
| Ngày xưa chùa ấy cầu duyên | Long ago, in that temple, you prayed for love |
| Giờ em thành bóng sư thiền lặng thinh | Now you are a silent figure deep in meditation |
| Bỏ buồn, bỏ nhớ sau mình | Leaving sorrow and longing behind you |
| Âm thầm sớm mõ, chiều kinh mặc đời. | Quiet dawn bells, evening sutras, the world let go. |

## Kịch bản ghi âm (chỉ giọng)

`/` = ngừng ngắn · `//` = ngừng lâu (khoảng 2 giây)

```
Xin chào cả nhà, tôi là Hà Hồ. /
Mời mọi người cùng nghe bài thơ "Thăm lại chùa xưa" của bố tôi, nhà thơ Hồ Đình Bắc. //

Eo thon mặc áo nâu sồng /
Khăn chùa thay mái tóc bồng ngày xưa /
Để giờ mõ sớm, kinh trưa /
Mắt buồn xuân cũ như vừa ướt mi. //

Thinh không chùa vắng từ bi /
Quên sao ngày ấy em đi lễ chùa /
Tóc dài vương những sợi mưa /
Cầu duyên khi tuổi mới vừa sang xuân. //

Không ngờ duyên nợ phong trần /
Tình tan như nắng qua sân dãi dầu /
Còn đâu duyên lễ, duyên cầu /
Khói hương chùa vắng, tình đầu ai quên? //

Ngày xưa chùa ấy cầu duyên /
Giờ em thành bóng sư thiền lặng thinh /
Bỏ buồn, bỏ nhớ sau mình /
Âm thầm sớm mõ, chiều kinh mặc đời.
```

## Scene

Hà Hồ asked for a real-looking pagoda and sent photos found online (press photos with a watermark). Those photos are not used, to avoid copyright claims. The scene is drawn entirely by code in the style of a northern mountain pagoda, with no copying of any one photo:

- A forested hill under a soft sky, with a white stupa (bảo tháp) on the top, pines and granite boulders.
- A stone terrace with a red railing. On it stands the main hall: orange tiles, white ridges, upswept roof corners (đao cong), red columns, white end pillars and a two-tier pavilion above. There are side halls, a bell pavilion (gác chuông) with a bronze bell, and an incense urn. Stone stairs with red handrails run down the hillside, and pines frame the foreground.
- **Stanza 1:** a misty morning. The nun, in a brown robe and head scarf, stands on the terrace with her palms together.
- **Stanza 2:** a faded, rainy memory of spring. The girl of long ago, with long black hair and a white áo dài, climbs the stairs in the rain.
- **Stanza 3:** the sun comes out. On "Tình tan như nắng qua sân" a patch of sunlight slides across the terrace and fades.
- **Stanza 4:** dusk. Lamps are lit for the evening sutras, and the nun stands by the incense urn as the smoke rises.
- **Music:** sáo trúc with a synthesized temple bell (chuông chùa) struck at the start and again as the poem ends.

## Render

`timing.json` holds the line start times taken from Hà Hồ's recording. They were found with pause detection, and each line was checked against the lục bát rhythm: 6-syllable lines run about 2 s and 8-syllable lines about 3 s. The recording is not in the repo. It is trimmed to [0.9, 64.5] s and starts at video t = 0.8 s.

```bash
python3 music.py music.wav sao
ffmpeg -i voice.m4a -af "atrim=0.9:64.5,asetpts=N/SR/TB,afade=t=in:d=0.2,highpass=f=80,afftdn=nf=-30,acompressor=threshold=-24dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,adelay=800:all=1,aresample=44100,aformat=channel_layouts=stereo" voice_clean.wav
for r in "0 18.16 p1" "18.16 36.32 p2" "36.32 54.48 p3" "54.48 72.62 p4"; do set -- $r; python3 silk.py full $1 $2 $3.mp4 & done; wait
printf "file '%s'\n" p1.mp4 p2.mp4 p3.mp4 p4.mp4 > list.txt
ffmpeg -f concat -i list.txt -i voice_clean.wav -i music.wav -filter_complex "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -movflags +faststart tham-lai-chua-xua.mp4
```
