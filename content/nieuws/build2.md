---
title: "Build, vervolg"
date: 2023-06-03T12:07:28Z
draft: false
tags: ['site']
---

't Is nog altijd geen échte build of zo, maar `xcopy public \\files\mvuijlst\www\users /s /y` is weg en vervangen door `robocopy public \\files\mvuijlst\www\users /MIR /Z /W:5 /COPY:DT /XC`. 

Ik had er nog nooit van gehoord, maar Robust File Copy zit blijkbaar al sinds Windows NT 4.0 in de NT Resource Kit, en sinds 2008 in alle Windows. Zot. 