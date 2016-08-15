import numpy as np
import os.path as osp

__all__ = [
  'Run'
]

### Is a collection of images
class Run(object):
  def __init__(self, timestamps, paths,
               source ='none', type = 'info',
               meta_info = None, run_info = None,
               index_info = None,
               images = None, image_index = None,
               name = 'run', data_root = './'):
    super(Run, self).__init__()

    self._timestamps = timestamps
    self._paths = paths
    self._source = source
    self._meta_info = dict() if meta_info is None else meta_info
    self._run_info = dict() if run_info is None else run_info
    self._type = type

    self._index_info = index_info

    self._data_root = data_root

    self._name = name

    if type != 'info':
      self._imgs = images

      if image_index is None and self._imgs is not None:
        self._image_index = np.arange(self._imgs.shape[0])
      else:
        self._image_index = image_index
    else:
      from crayimage.runutils import read_info_file

      self._imgs = [
        read_info_file(osp.join(data_root, path))
        for path in self.paths
      ]

      self._image_index = range(self.paths.shape[0])

  @property
  def data_root(self):
    return self._data_root

  @property
  def timestamps(self):
    return self._timestamps

  @property
  def paths(self):
    return self._paths

  @property
  def source(self):
    return self._source

  @source.setter
  def source(self, value):
    self._source = value

  @property
  def meta_info(self):
    return self._meta_info

  @property
  def run_info(self):
    return self._run_info

  @run_info.setter
  def run_info(self, value):
    self._run_info.update(value)

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, value):
    self._name = value


  @property
  def type(self):
    return self._type

  @property
  def images(self):
    return self._imgs

  @property
  def abs_paths(self):
    import os.path as osp

    return np.array([
      osp.abspath(osp.join(self.data_root, path))
      for path in self.paths
    ])

  def __getitem__(self, item):
    if self._image_index is not None:
      indx = self._image_index[item]
    else:
      indx = None

    meta_info = dict()
    for k in self._meta_info:
      meta_info[k] = self._meta_info[k][item]

    return Run(
      timestamps=self._timestamps[item],
      paths=self._paths[item],
      source=self._source,
      type=self._type,
      meta_info=meta_info,
      run_info=self.run_info,
      index_info=self._index_info,
      images=self._imgs,
      image_index=indx,
      name=self._name,
      data_root=self._data_root
    )

  def __str__(self):
    pattern = 'Run(%s)(source = %s, type = %s, run_info = %s, meta_info = %s, timestamps = %s, paths = %s)'

    return pattern % (
      self._name, str(self._source), str(self._type), str(self._run_info),
      str(self._meta_info), str(self._timestamps), str(self._paths)
    )

  def __len__(self):
    return self._paths.shape[0]

  def random_subset(self, limit):
    limit = min(limit, len(self))
    indx = np.random.choice(len(self), limit, replace = False)
    indx = indx[np.argsort(self._timestamps[indx])]

    return self[indx]

  def _read_image(self, index):
    from crayimage.imgutils import get_reader
    reader = get_reader(self.type)

    return reader(osp.join(self.data_root, self._paths[index]))

  def get_img(self, index):
    if self._imgs is not None:
      return self._imgs[self._image_index[index]]
    else:
      return self._read_image(index)

  def __iter__(self):
    return self.read_run_iter()

  def read_run_iter(self):
    for i in xrange(len(self)):
      yield self.get_img(i)

  def read_run(self):
    if self.type is 'info':
      return self

    if self._imgs is None:
      imgs = None

      for i, img in enumerate(self):
        if imgs is None:
          imgs = np.ndarray(shape=(len(self),) + img.shape, dtype=img.dtype)

        imgs[i] = img

      return Run(
        timestamps=self._timestamps,
        paths=self._paths,
        source=self._source,
        type=self._type,
        meta_info=self._meta_info,
        run_info=self.run_info,
        index_info=self._index_info,
        images=imgs,
        name=self._name,
        data_root=self._data_root
      )
    else:
      return self

  def get_index_info(self):
    return {
      "path": [ path for path in self.paths ],
      "source" : self.source,
      "timestamp": self._index_info['timestamp'],
      "type": self.type,

      "info": self._index_info['info'],
      'run_info' : self.run_info
    }