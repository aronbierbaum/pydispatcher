"""Pydoc sub-class for generating documentation for entire packages"""
import pydoc, inspect, os, string
import sys, imp, os, stat, re, types, inspect
from reprlib import Repr


class DefaultFormatter(pydoc.HTMLDoc):
    def docmodule(self, object, name=None, mod=None, packageContext=None, *ignored):
        """Produce HTML documentation for a module object."""
        name = object.__name__  # ignore the passed-in name
        parts = name.split(".")
        links = []
        for i in range(len(parts) - 1):
            links.append(
                '<a href="%s.html"><font color="#ffffff">%s</font></a>'
                % (".".join(parts[: i + 1]), parts[i])
            )
        linkedname = ".".join(links + parts[-1:])
        head = "<big><big><strong>%s</strong></big></big>" % linkedname
        try:
            path = inspect.getabsfile(object)
            url = path
            if sys.platform == "win32":
                import nturl2path

                url = nturl2path.pathname2url(path)
            filelink = '<a href="file:%s">%s</a>' % (url, path)
        except TypeError:
            filelink = "(built-in)"
        info = []
        if hasattr(object, "__version__"):
            version = str(object.__version__)
            if version[:11] == "$" + "Revision: " and version[-1:] == "$":
                version = version[11:-1].strip()
            info.append("version %s" % self.escape(version))
        if hasattr(object, "__date__"):
            info.append(self.escape(str(object.__date__)))
        if info:
            head = head + " (%s)" % ", ".join(info)
        result = self.heading(
            head, "#ffffff", "#7799ee", '<a href=".">index</a><br>' + filelink
        )

        modules = inspect.getmembers(object, inspect.ismodule)

        classes, cdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isclass):
            if (inspect.getmodule(value) or object) is object:
                classes.append((key, value))
                cdict[key] = cdict[value] = "#" + key
        for key, value in classes:
            for base in value.__bases__:
                key, modname = base.__name__, base.__module__
                module = sys.modules.get(modname)
                if modname != name and module and hasattr(module, key):
                    if getattr(module, key) is base:
                        if key not in cdict:
                            cdict[key] = cdict[base] = modname + ".html#" + key
        funcs, fdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isroutine):
            if inspect.isbuiltin(value) or inspect.getmodule(value) is object:
                funcs.append((key, value))
                fdict[key] = "#-" + key
                if inspect.isfunction(value):
                    fdict[value] = fdict[key]
        data = []
        for key, value in inspect.getmembers(object, pydoc.isdata):
            if key not in ["__builtins__", "__doc__"]:
                data.append((key, value))

        doc = self.markup(pydoc.getdoc(object), self.preformat, fdict, cdict)
        doc = doc and "<tt>%s</tt>" % doc
        result = result + "<p>%s</p>\n" % doc

        packageContext.clean(classes, object)
        packageContext.clean(funcs, object)
        packageContext.clean(data, object)

        if hasattr(object, "__path__"):
            modpkgs = []
            modnames = []
            for file in os.listdir(object.__path__[0]):
                path = os.path.join(object.__path__[0], file)
                modname = inspect.getmodulename(file)
                if modname and modname not in modnames:
                    modpkgs.append((modname, name, 0, 0))
                    modnames.append(modname)
                elif pydoc.ispackage(path):
                    modpkgs.append((file, name, 1, 0))
            modpkgs.sort()
            contents = self.multicolumn(modpkgs, self.modpkglink)
            ##			result = result + self.bigsection(
            ##				'Package Contents', '#ffffff', '#aa55cc', contents)
            result = result + self.moduleSection(object, packageContext)
        elif modules:
            contents = self.multicolumn(
                modules, lambda item, s=self: s.modulelink(item[1])
            )
            result = result + self.bigsection("Modules", "#fffff", "#aa55cc", contents)

        if classes:
            classlist = [key_value[1] for key_value in classes]
            contents = [self.formattree(inspect.getclasstree(classlist, 1), name)]
            for key, value in classes:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection(
                "Classes", "#ffffff", "#ee77aa", "".join(contents)
            )
        if funcs:
            contents = []
            for key, value in funcs:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection(
                "Functions", "#ffffff", "#eeaa77", "".join(contents)
            )
        if data:
            contents = []
            for key, value in data:
                contents.append(self.document(value, key))
            result = result + self.bigsection(
                "Data", "#ffffff", "#55aa55", "<br>\n".join(contents)
            )
        if hasattr(object, "__author__"):
            contents = self.markup(str(object.__author__), self.preformat)
            result = result + self.bigsection("Author", "#ffffff", "#7799ee", contents)
        if hasattr(object, "__credits__"):
            contents = self.markup(str(object.__credits__), self.preformat)
            result = result + self.bigsection("Credits", "#ffffff", "#7799ee", contents)

        return result

    def classlink(self, object, modname):
        """Make a link for a class."""
        name, module = object.__name__, sys.modules.get(object.__module__)
        if hasattr(module, name) and getattr(module, name) is object:
            return '<a href="%s.html#%s">%s</a>' % (module.__name__, name, name)
        return pydoc.classname(object, modname)

    def moduleSection(self, object, packageContext):
        """Create a module-links section for the given object (module)"""
        modules = inspect.getmembers(object, inspect.ismodule)
        packageContext.clean(modules, object)
        packageContext.recurseScan(modules)

        if hasattr(object, "__path__"):
            modpkgs = []
            modnames = []
            for file in os.listdir(object.__path__[0]):
                path = os.path.join(object.__path__[0], file)
                modname = inspect.getmodulename(file)
                if modname and modname not in modnames:
                    modpkgs.append((modname, object.__name__, 0, 0))
                    modnames.append(modname)
                elif pydoc.ispackage(path):
                    modpkgs.append((file, object.__name__, 1, 0))
            modpkgs.sort()
            # do more recursion here...
            for (modname, name, ya, yo) in modpkgs:
                packageContext.addInteresting(".".join((object.__name__, modname)))
            items = []
            for (modname, name, ispackage, isshadowed) in modpkgs:
                try:
                    # get the actual module object...
                    ##					if modname == "events":
                    ##						import pdb
                    ##						pdb.set_trace()
                    module = pydoc.safeimport("%s.%s" % (name, modname))
                    description, documentation = pydoc.splitdoc(inspect.getdoc(module))
                    if description:
                        items.append(
                            """%s -- %s"""
                            % (
                                self.modpkglink((modname, name, ispackage, isshadowed)),
                                description,
                            )
                        )
                    else:
                        items.append(
                            self.modpkglink((modname, name, ispackage, isshadowed))
                        )
                except:
                    items.append(
                        self.modpkglink((modname, name, ispackage, isshadowed))
                    )
            contents = "<br>".join(items)
            result = self.bigsection("Package Contents", "#ffffff", "#aa55cc", contents)
        elif modules:
            contents = self.multicolumn(
                modules, lambda item, s=self: s.modulelink(item[1])
            )
            result = self.bigsection("Modules", "#fffff", "#aa55cc", contents)
        else:
            result = ""
        return result


class AlreadyDone(Exception):
    pass


class PackageDocumentationGenerator:
    """A package document generator creates documentation
    for an entire package using pydoc's machinery.

    baseModules -- modules which will be included
        and whose included and children modules will be
        considered fair game for documentation
    destinationDirectory -- the directory into which
        the HTML documentation will be written
    recursion -- whether to add modules which are
        referenced by and/or children of base modules
    exclusions -- a list of modules whose contents will
        not be shown in any other module, commonly
        such modules as OpenGL.GL, wxPython.wx etc.
    recursionStops -- a list of modules which will
        explicitly stop recursion (i.e. they will never
        be included), even if they are children of base
        modules.
    formatter -- allows for passing in a custom formatter
        see DefaultFormatter for sample implementation.
    """

    def __init__(
        self,
        baseModules,
        destinationDirectory=".",
        recursion=1,
        exclusions=(),
        recursionStops=(),
        formatter=None,
    ):
        self.destinationDirectory = os.path.abspath(destinationDirectory)
        self.exclusions = {}
        self.warnings = []
        self.baseSpecifiers = {}
        self.completed = {}
        self.recursionStops = {}
        self.recursion = recursion
        for stop in recursionStops:
            self.recursionStops[stop] = 1
        self.pending = []
        for exclusion in exclusions:
            try:
                self.exclusions[exclusion] = pydoc.locate(exclusion)
            except pydoc.ErrorDuringImport as value:
                self.warn(
                    """Unable to import the module %s which was specified as an exclusion module"""
                    % (repr(exclusion))
                )
        self.formatter = formatter or DefaultFormatter()
        for base in baseModules:
            self.addBase(base)

    def warn(self, message):
        """Warnings are used for recoverable, but not necessarily ignorable conditions"""
        self.warnings.append(message)

    def info(self, message):
        """Information/status report"""
        print(message)

    def addBase(self, specifier):
        """Set the base of the documentation set, only children of these modules will be documented"""
        try:
            self.baseSpecifiers[specifier] = pydoc.locate(specifier)
            self.pending.append(specifier)
        except pydoc.ErrorDuringImport as value:
            self.warn(
                """Unable to import the module %s which was specified as a base module"""
                % (repr(specifier))
            )

    def addInteresting(self, specifier):
        """Add a module to the list of interesting modules"""
        if self.checkScope(specifier):
            ##			print "addInteresting", specifier
            self.pending.append(specifier)
        else:
            self.completed[specifier] = 1

    def checkScope(self, specifier):
        """Check that the specifier is "in scope" for the recursion"""
        if not self.recursion:
            return 0
        items = specifier.split(".")
        stopCheck = items[:]
        while stopCheck:
            name = ".".join(items)
            if self.recursionStops.get(name):
                return 0
            elif self.completed.get(name):
                return 0
            del stopCheck[-1]
        while items:
            if self.baseSpecifiers.get(".".join(items)):
                return 1
            del items[-1]
        # was not within any given scope
        return 0

    def process(self):
        """Having added all of the base and/or interesting modules,
        proceed to generate the appropriate documentation for each
        module in the appropriate directory, doing the recursion
        as we go."""
        try:
            while self.pending:
                try:
                    if self.pending[0] in self.completed:
                        raise AlreadyDone(self.pending[0])
                    self.info("""Start %s""" % (repr(self.pending[0])))
                    object = pydoc.locate(self.pending[0])
                    self.info("""   ... found %s""" % (repr(object.__name__)))
                except AlreadyDone:
                    pass
                except pydoc.ErrorDuringImport as value:
                    self.info("""   ... FAILED %s""" % (repr(value)))
                    self.warn(
                        """Unable to import the module %s""" % (repr(self.pending[0]))
                    )
                except (SystemError, SystemExit) as value:
                    self.info("""   ... FAILED %s""" % (repr(value)))
                    self.warn(
                        """Unable to import the module %s""" % (repr(self.pending[0]))
                    )
                except Exception as value:
                    self.info("""   ... FAILED %s""" % (repr(value)))
                    self.warn(
                        """Unable to import the module %s""" % (repr(self.pending[0]))
                    )
                else:
                    page = self.formatter.page(
                        pydoc.describe(object),
                        self.formatter.docmodule(
                            object,
                            object.__name__,
                            packageContext=self,
                        ),
                    )
                    file = open(
                        os.path.join(
                            self.destinationDirectory,
                            self.pending[0] + ".html",
                        ),
                        "w",
                    )
                    file.write(page)
                    file.close()
                    self.completed[self.pending[0]] = object
                del self.pending[0]
        finally:
            for item in self.warnings:
                print(item)

    def clean(self, objectList, object):
        """callback from the formatter object asking us to remove
        those items in the key, value pairs where the object is
        imported from one of the excluded modules"""
        for key, value in objectList[:]:
            for excludeObject in list(self.exclusions.values()):
                if hasattr(excludeObject, key) and excludeObject is not object:
                    if getattr(excludeObject, key) is value or (
                        hasattr(excludeObject, "__name__")
                        and excludeObject.__name__ == "Numeric"
                    ):
                        objectList[:] = [(k, o) for k, o in objectList if k != key]

    def recurseScan(self, objectList):
        """Process the list of modules trying to add each to the
        list of interesting modules"""
        for key, value in objectList:
            self.addInteresting(value.__name__)


if __name__ == "__main__":
    excludes = [
        "OpenGL.GL",
        "OpenGL.GLU",
        "OpenGL.GLUT",
        "OpenGL.GLE",
        "OpenGL.GLX",
        "wxPython.wx",
        "Numeric",
        "_tkinter",
        "Tkinter",
    ]

    modules = [
        "OpenGLContext.debug",
        ##		"wxPython.glcanvas",
        ##		"OpenGL.Tk",
        ##		"OpenGL",
    ]
    PackageDocumentationGenerator(
        baseModules=modules,
        destinationDirectory="z:\\temp",
        exclusions=excludes,
    ).process()
