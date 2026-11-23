# Khoảnh khắc đông về — The Moment Winter Comes

Thơ: Hồ Đình Bắc (20/11/2011) · Giọng đọc: Hà Hồ

The poem has 20 lục bát lines with no stanza breaks. For the screen they are grouped four by four. The manuscript's indentation is not kept.

## Lời thơ / Poem (transcribed exactly from the manuscript)

| Tiếng Việt | English subtitle |
|---|---|
| Giữa vườn cơn gió lạnh se | A chill wind stirs across the garden |
| Chắc là đông sớm chợt về đấy thôi | Winter must have come early, all of a sudden |
| Trời xanh giờ đã xám rồi | The blue sky has already turned to grey |
| Còn đâu cái nắng đầy trời cuối thu | Gone is the late-autumn sun that filled the sky |
| | |
| Đêm về lạnh cả lời ru | Night falls, and even the lullabies grow cold |
| Trăng suông lùa gió ù ù vào đông. | A pale moon, the wind moaning into winter. |
| Hết mưa giờ nước ngấn sông | The rains are gone, their mark left on the river |
| Con thuyền lơ đễnh vượt dòng lạnh trôi | A boat drifts idly across the cold current |
| | |
| Lũ tàn trơ cả đất bồi | The floods recede, baring the rich silt banks |
| Sông êm êm chảy đê thôi gồng mình. | The river flows calm, the dike no longer strains. |
| Bãi bờ cải đã lên xanh | Mustard greens have sprouted along the banks |
| Hẹn ngày hoa nở vàng tình chia xa. | Promising yellow blooms for loves kept apart. |
| | |
| Chớm đông mà đến chơi nhà | In early winter I come to visit your home |
| Chắc em đang bận đồng xa, đồng gần | You must be busy in the fields, near and far |
| Mải mê với vụ đông xuân | Wrapped up in the winter-spring crop |
| Bầu ngô, bầu mạ trên sân tối ngày. | Corn and rice seedlings in the yard all day. |
| | |
| Đến rồi anh ở lại đây | Now that I am here, I will stay |
| Cùng em vun xới vườn cây em trồng | And help you tend the garden you have planted |
| Chăm hoa mầu nữa ngoài đồng | And care for the crops out in the fields |
| Cho xong mùa vụ thắm nồng duyên quê. | Till the season's work is done, our country love warm. |

## Kịch bản ghi âm (chỉ giọng)

`/` = ngừng ngắn · `//` = ngừng lâu (khoảng 2 giây)

```
Xin chào cả nhà, tôi là Hà Hồ. /
Mời mọi người cùng nghe bài thơ "Khoảnh khắc đông về" của bố tôi, nhà thơ Hồ Đình Bắc. //

Giữa vườn cơn gió lạnh se /
Chắc là đông sớm chợt về đấy thôi /
Trời xanh giờ đã xám rồi /
Còn đâu cái nắng đầy trời cuối thu //

Đêm về lạnh cả lời ru /
Trăng suông lùa gió ù ù vào đông. /
Hết mưa giờ nước ngấn sông /
Con thuyền lơ đễnh vượt dòng lạnh trôi //

Lũ tàn trơ cả đất bồi /
Sông êm êm chảy đê thôi gồng mình. /
Bãi bờ cải đã lên xanh /
Hẹn ngày hoa nở vàng tình chia xa. //

Chớm đông mà đến chơi nhà /
Chắc em đang bận đồng xa, đồng gần /
Mải mê với vụ đông xuân /
Bầu ngô, bầu mạ trên sân tối ngày. //

Đến rồi anh ở lại đây /
Cùng em vun xới vườn cây em trồng /
Chăm hoa mầu nữa ngoài đồng /
Cho xong mùa vụ thắm nồng duyên quê.
```

## Scene

The scene is lifelike, built on the same village scene as `mua-dong-thuong-me/` and drawn entirely by code.

- **Stanza 1:** the late-autumn sun fades and the sky turns grey on "Trời xanh giờ đã xám rồi". Dry leaves blow in the wind.
- **Stanza 2:** moonlit night. A pale moon appears, the windows are lamplit, and a small boat drifts across the river.
- **Stanza 3:** a calm morning. Rows of mustard greens sprout on the silt bank on "Bãi bờ cải đã lên xanh", and yellow mustard flowers open on "hoa nở vàng".
- **Stanza 4:** a working day. She (em, in nón lá) is bent over the field, and he (anh) walks up the path to her house. Corn and rice seedling trays appear on the brick yard on "Bầu ngô, bầu mạ trên sân".
- **Stanza 5:** warm light. He has a hoe and works beside her in the field, and the fields green up with the winter crop.

## Render

Music: **sáo trúc** (`python3 music.py music.wav sao`), chosen by Hà Hồ.

`timing.json` holds the line start times taken from Hà Hồ's recording. They were found with pause detection, and each line was checked against the lục bát rhythm: 6-syllable lines run about 2 s and 8-syllable lines about 3 s. The recording is not in the repo. It is trimmed to [1.0, 74.0] s and starts at video t = 0.8 s.

```bash
python3 music.py music.wav sao
ffmpeg -i voice.m4a -af "atrim=1.0:74.0,asetpts=N/SR/TB,afade=t=in:d=0.2,highpass=f=80,afftdn=nf=-30,acompressor=threshold=-24dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,adelay=800:all=1,aresample=44100,aformat=channel_layouts=stereo" voice_clean.wav
for r in "0 20.5 p1" "20.5 41.0 p2" "41.0 61.5 p3" "61.5 82.02 p4"; do set -- $r; python3 silk.py full $1 $2 $3.mp4 & done; wait
printf "file '%s'\n" p1.mp4 p2.mp4 p3.mp4 p4.mp4 > list.txt
ffmpeg -f concat -i list.txt -i voice_clean.wav -i music.wav -filter_complex "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -movflags +faststart khoanh-khac-dong-ve.mp4
```
