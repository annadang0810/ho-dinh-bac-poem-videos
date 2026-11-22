# Dòng sông nỗi nhớ — The River of Longing

Thơ: Hồ Đình Bắc · Giọng đọc: Hà Hồ

In the poet's manuscript the poem carries the dedication "Gửi G. Hưng Yên". It is left off the video for now.

## Lời thơ / Poem (transcribed exactly from the manuscript)

| Tiếng Việt | English subtitle |
|---|---|
| Em lại về nơi ấy cuối dòng sông | You have gone back to where the river ends |
| Con sông Hồng ngày đêm sóng vỗ | The Red River, waves lapping night and day |
| Ôi tiếng sóng hay tiếng lòng ai đó | Is it the waves, or someone's aching heart? |
| Sông rộng dài nỗi nhớ rộng dài theo. | Long as the river runs, so runs my longing. |
| | |
| Đã bao mùa mưa lũ mình xa nhau | So many flood seasons we have been apart |
| Con nước đầy vơi mái chèo vỗ nhịp | The water rises and falls to the beat of oars |
| Tiếng cuốc đêm đêm gọi về tha thiết | Night after night the waterhen calls, so tender |
| Cứ long bong nước vỡ vọng hai bờ | Water breaking, echoing from shore to shore |
| | |
| Em đi xa nhãn chín đã mấy mùa, | Since you left, the longans have ripened many times, |
| Đã mấy mùa lũ về ngập bến, | Many seasons the floods have drowned the landing, |
| Đã bao đêm mưa nguồn chớp biển. | Many nights of mountain rain and lightning at sea. |
| Có đêm nào thao thức nhớ người xưa? | Was there one night you lay awake, missing me? |
| | |
| Nước sông đầy mà trời vẫn còn mưa. | The river is full, and still the rain comes down. |
| Để khắc khoải lòng anh mùa bão lũ. | My heart aches all through the storm season. |
| Cánh buồm nhỏ em chưa tìm bến đỗ | Your little sail has yet to find a harbour |
| Em xa ơi nghe tiếng cuốc gọi buồn! | O my faraway love, hear the waterhen's sad call! |

## Kịch bản ghi âm (chỉ giọng, không quay mặt)

`/` = ngừng ngắn · `//` = ngừng lâu (khoảng 2 giây)

```
Xin chào cả nhà, tôi là Hà Hồ. /
Mời mọi người cùng nghe bài thơ "Dòng sông nỗi nhớ" của bố tôi, nhà thơ Hồ Đình Bắc. //

Em lại về nơi ấy cuối dòng sông /
Con sông Hồng ngày đêm sóng vỗ /
Ôi tiếng sóng hay tiếng lòng ai đó /
Sông rộng dài nỗi nhớ rộng dài theo. //

Đã bao mùa mưa lũ mình xa nhau /
Con nước đầy vơi mái chèo vỗ nhịp /
Tiếng cuốc đêm đêm gọi về tha thiết /
Cứ long bong nước vỡ vọng hai bờ //

Em đi xa nhãn chín đã mấy mùa, /
Đã mấy mùa lũ về ngập bến, /
Đã bao đêm mưa nguồn chớp biển. /
Có đêm nào thao thức nhớ người xưa? //

Nước sông đầy mà trời vẫn còn mưa. /
Để khắc khoải lòng anh mùa bão lũ. /
Cánh buồm nhỏ em chưa tìm bến đỗ /
Em xa ơi nghe tiếng cuốc gọi buồn! //

Cảm ơn mọi người đã lắng nghe.
```

## Scene (chosen from the poem's own images)

- The Red River is the centre of the picture: wide, silt-coloured, with ink ripple strokes and a small wooden landing (bến).
- A little sampan with a small sail drifts slowly down the river for the whole poem and never reaches the landing ("Cánh buồm nhỏ em chưa tìm bến đỗ").
- An old longan tree stands on the left; ripe longan clusters appear in stanza 3 ("nhãn chín"). Bamboo stands on the dike on the right.
- A white-breasted waterhen (chim cuốc) stands on the bank whenever its call is mentioned (stanza 2 line 3 and the last line).
- The light moves from golden afternoon through rose dusk to a grey-blue rainy night. Rain starts in stanza 3, distant lightning flashes on "chớp biển", and rain rings form on the river.

## Render

```bash
cd dong-song-noi-nho
python3 silk.py stills 3 14 27 36.3 50 59
(python3 silk.py full 0 31 a.mp4 & python3 silk.py full 31 61.5 b.mp4 & wait)
```

`timing.json` holds the line start times taken from Hà Hồ's recording. The times were found with pause detection and energy minima, then checked against the syllable count of each line. The recording itself is not in the repo. The long pause after the intro (14.0–24.3 s) is cut, and the voice starts at video t = 1.0 s.

```bash
python3 music.py music.wav                      # music, ducked to 25% under the voice
ffmpeg -i voice.m4a -filter_complex "[0:a]atrim=2.3:14.0,asetpts=N/SR/TB[a];[0:a]atrim=24.3:88.5,asetpts=N/SR/TB,afade=t=in:d=0.3[b];[a][b]concat=n=2:v=0:a=1,highpass=f=80,afftdn=nf=-30,acompressor=threshold=-24dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,adelay=1000:all=1,aresample=44100,aformat=channel_layouts=stereo[v]" -map "[v]" voice_clean.wav
for r in "0 21.2 p1" "21.2 42.3 p2" "42.3 63.4 p3" "63.4 84.54 p4"; do set -- $r; python3 silk.py full $1 $2 $3.mp4 & done; wait
printf "file '%s'\n" p1.mp4 p2.mp4 p3.mp4 p4.mp4 > list.txt
ffmpeg -f concat -i list.txt -i voice_clean.wav -i music.wav -filter_complex "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k dong-song-noi-nho.mp4
```
