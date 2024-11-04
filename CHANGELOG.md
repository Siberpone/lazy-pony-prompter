### 2024-11-04

* Added support for [NoobAI v1.0](https://civitai.com/models/833294/noobai-xl-nai-xl) model

### 2024-10-29

**1.1.0** release
* Added [Danbooru](https://danbooru.donmai.us) as tag source
* Added support for [SeaArt Furry XL V1](https://civitai.com/models/391781/seaart-furry-xl-10) model
* Import/Export functions for prompts and filters
* Prompt info panel is now more compact and readable
* Minor ComfyUI nodes improvements (notably: updater dummy is no longer needed)
* Tons of refactoring and behind-the-scene improvements

### 2024-07-03

**1.0.0 release**
* Overhauled UI
* New tag filtering system with filter management and pattern substitutions
* Filter prompts by content rating (Safe/Questionable/Explicit)
* Increased maximum prompts limit to 1500
* Improved status reporting and logging

### 2024-01-17

* Added custom prompt templates support
* Added some basic settings ui
* Added automatic prompt formatter selection
* Sources can now fetch tags from image URL
* Minor UI improvements
* Improved error handling

### 2023-10-23

* Added experimental ComfyUI support
* Prompts cache is now stored in binary which should reduce size and load time
* Lots of code refactoring and reorganising

### 2023-10-19

* Removed legacy cache format updater. Hopefully everyone updated at this point :)

### 2023-10-13

* Small UI fixes and improvements
* e621 formatters improvements
* Improved formatting for EasyFluff
* Added PDV5 formatter for e621

### 2023-10-02

* Added simple globbing support to tag filter

### 2023-10-01

* Added different tag sources and prompt formats support
* Added support for e621.net as tag source
* Added basic support for EasyFluff model
* Added support for standard [A1111 styles feature](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#styles)
* Removed Prefix and Suffix textboxes since A1111 styles can be used for the same purpose

### 2023-08-04

* Renamed "Saving & Loading" to "Prompts Manager"
* Refined Prompts Manager UI
* Added confirmation dialog for deleting/overwriting prompt collections
* Added option to autofill Suffix, Prefix and Tag Filter when loading prompts

### 2023-08-03

* Refined UI layout

### 2023-08-02

* Renamed append/prepend to prefix/suffix respectively. **NOTE :** this affects `a1111_ui.json` config options. Rename manually if you created a custom `my_a1111_ui.json` config
* Prefix, Suffix and User Tag Filters are now applied dynamically on each generation
* Previously saved prompts can now be deleted from cache via `Delete` button
* Added extra metadata to saved prompts (query, filter and sorting type). Could be useful if you want to rerun a query
* Parentheses are now only escaped in the core prompt (you can now properly use attention syntax in prefix and suffix)

### 2023-07-26

* Refined and expanded tag filtering

### 2023-07-22

* Refined config system
* Added user-defined configs

### 2023-07-21

* Added custom Prepending/Appending text to prompts
* Added extra tag filter
* Refined UI layout

### 2023-07-20

* Hid save/load into accordion
* Added UI config
