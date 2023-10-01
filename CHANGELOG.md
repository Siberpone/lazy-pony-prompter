### 2023-10-01

* Added different tag sources and prompt formats support
* Added support for e632.net as tag source
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
