Here are some more informal instructions for running CrunchyFrog on !MacOS. Thanks to mjs7231 for sharing them on the [mailing list](http://groups.google.com/group/crunchyfrog/browse_thread/thread/74b41cd152a64023)!

### Installed MacPort Packages ###

  * gtk2 @2.18.2\_1+x11 (active)
  * gtksourceview2 @2.6.2\_0 (active)
  * py26-cairo @1.8.8\_0 (active)
  * py26-configobj @4.5.2\_0 (active)
  * py26-gobject @2.18.0\_0 (active)
  * py26-gtk @2.16.0\_0 (active)
  * py26-xdg @0.16\_0 (active)
  * python26 @2.6.4\_0+darwin (active)


### Additional Packages (So its not fugly) ###

  * gtk-chtheme @0.3.1\_0 (active)
  * gtk2-aurora @1.5.1\_0 (active)
  * hicolor-icon-theme @0.11\_0 (active)


### Notes ###

  1. Make sure to use the Python interpreter installed by MacPorts.
  1. To it working in it's basic condition, you should only need the top packages.
  1. You can fix it visual a bit by installing the gtk items in the second list.  Run gtk-chtheme to choose the theme Aurora (or whatever you prefer).
  1. Installing the hicolor-icon-theme stops an error from being reported, but we still get a lot of warnings about icons that cannot be found.