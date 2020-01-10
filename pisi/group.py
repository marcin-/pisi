# -*- coding: utf-8 -*-
#
# Copyright (C) 2009, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import pisi
import pisi.pxml.xmlfile as xmlfile
import pisi.pxml.autoxml as autoxml


class Error(pisi.Error):
    pass


class Group(xmlfile.XmlFile, metaclass=autoxml.autoxml):
    """Representation for group declarations"""

    t_Name = [autoxml.String, autoxml.mandatory]
    t_LocalName = [autoxml.LocalText, autoxml.mandatory]
    t_Icon = [autoxml.String, autoxml.optional]


class Groups(xmlfile.XmlFile, metaclass=autoxml.autoxml):
    """Representation for component declarations"""

    tag = "PISI"

    t_Groups = [[Group], autoxml.optional, "Groups/Group"]
