import subprocess
import os
import json
import xml.etree.ElementTree as ET

LOG = None
try:
    from cloudinit import log
    LOG = log.getLogger(__name__)
except AttributeError:
    LOG = log

DS = None
try:
    from cloudinit import sources
    DS = sources.DataSource
except ImportError:
    from cloudinit import DataSource
    DS = DataSource.DataSource

try:
    from cloudinit import stages
except ImportError:
    stages = None

class DataSourceVmwareGuestinfo(DS):
    def get_data(self):
        rpctool = self._which("vmware-rpctool")
        if rpctool is None:
            LOG.info("No vmware-rpctool found (PATH is %s)" %  os.environ.get('PATH'))
            return False
        try:
            LOG.debug("Running %s 'info-get guestinfo.cloudinit.userdata'", rpctool)
            p1 = subprocess.Popen([rpctool,"info-get guestinfo.cloudinit.userdata"], stdout=subprocess.PIPE, stdin=None)
            self.userdata_raw, _ = p1.communicate()
            if p1.returncode != 0:
                LOG.error("vmware-rpctool exited with %d" % p1.returncode)
                return False
            LOG.debug("Running %s 'info-get guestinfo.cloudinit.metadata'", rpctool)
            p2 = subprocess.Popen([rpctool,"info-get guestinfo.cloudinit.metadata"], stdout=subprocess.PIPE, stdin=None)
            meta, _ = p2.communicate()
            if p2.returncode not in [0, 1]:
                # 0 = success
                # 1 = Value not found
                LOG.error("vmware-rpctool exited with %d" % p2.returncode)
                return False
            if meta != "":
                try:
                    self.metadata = json.loads(meta)
                except ValueError as e:
                    LOG.error("Failed to decode json %r: %r", e, meta)
                    return False
            else:
                self.metadata = {}
            LOG.debug("Running %s 'info-get guestinfo.ovfEnv'", rpctool)
            p3 = subprocess.Popen([rpctool,"info-get guestinfo.ovfEnv"], stdout=subprocess.PIPE, stdin=None)
            ovf, _ = p3.communicate()
            if p3.returncode not in [0, 1]:
                # 0 = success
                # 1 = Value not found
                LOG.error("vmware-rpctool exited with %d" % p3.returncode)
                return False
            else:
              try:
                  self.metadata.update( self._parse_ovf(ovf) )
              except ValueError as e:
                  LOG.error("Failed to parse ovf %r: %r", e, ovf)
                  return False
        except OSError as e:
            LOG.error(e)
            return False
        return True

    def _parse_ovf(ovf):
        """Parses ovfEnv guestinfo"""
        if ovf == "":
          return {}
        tree = ET.fromstring(ovf)
        rt = {}
        for props in tree.findall("{http://schemas.dmtf.org/ovf/environment/1}PropertySection"):
          for prop in props:
              rt[ prop.attrib["{http://schemas.dmtf.org/ovf/environment/1}key"] ] = prop.attrib["{http://schemas.dmtf.org/ovf/environment/1}value"]
        return rt

    def _which(self, filename):
        """Finds an executable"""
        locations = os.environ.get("PATH").split(os.pathsep)
        candidates = []
        for location in locations:
            candidate = os.path.join(location, filename)
            if os.path.isfile(candidate):
                return candidate
        return None


def get_datasource_list(depends):
    """
    Return a list of data sources that match this set of dependencies
    """
    return [DataSourceVmwareGuestinfo]

def main():
    log.setupLogging()
    init = stages.Init()
    s = DataSourceVmwareGuestinfo(init.cfg, init.distro, init.paths)
    if s.get_data():
        print "Found data"
    else:
        print "Didn't find data"
    print "userdata_raw: %r" % s.userdata_raw
    print "metadata: %r" % s.metadata

if __name__ == "__main__":
    main()
