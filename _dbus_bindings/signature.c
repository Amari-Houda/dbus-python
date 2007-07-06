/* Implementation of Signature type for D-Bus bindings.
 *
 * Copyright (C) 2006 Collabora Ltd.
 *
 * Licensed under the Academic Free License version 2.1
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 */

#include <Python.h>
#include <structmember.h>

#include <stdint.h>

#include "dbus_bindings-internal.h"
#include "types-internal.h"

static PyTypeObject DBusPySignature_Type;

PyDoc_STRVAR(Signature_tp_doc,
"A string subclass whose values are restricted to valid D-Bus\n"
"signatures. When iterated over, instead of individual characters it\n"
"produces Signature instances representing single complete types.\n"
"\n"
"Constructor::\n"
"\n"
"    ``Signature(value: str or unicode[, variant_level: int]) -> Signature``\n"
"\n"
"``value`` must be a valid D-Bus signature (zero or more single complete\n"
"types).\n"
"\n"
"``variant_level`` must be non-negative; the default is 0.\n"
"\n"
":IVariables:\n"
"  `variant_level` : int\n"
"    Indicates how many nested Variant containers this object\n"
"    is contained in: if a message's wire format has a variant containing a\n"
"    variant containing a signature, this is represented in Python by a\n"
"    Signature with variant_level==2.\n"
);

typedef struct {
    PyObject_HEAD
    PyObject *string;
    DBusSignatureIter iter;
} SignatureIter;

static void
SignatureIter_tp_dealloc (SignatureIter *self)
{
    Py_XDECREF(self->string);
    self->string = NULL;
    PyObject_Del(self);
}

static PyObject *
SignatureIter_tp_iternext (SignatureIter *self)
{
    char *sig;
    PyObject *obj;

    /* Stop immediately if finished or not correctly initialized */
    if (!self->string) return NULL;

    sig = dbus_signature_iter_get_signature(&(self->iter));
    if (!sig) return PyErr_NoMemory();
    obj = PyObject_CallFunction((PyObject *)&DBusPySignature_Type, "s", sig);
    dbus_free(sig);
    if (!obj) return NULL;

    if (!dbus_signature_iter_next(&(self->iter))) {
        /* mark object as having been finished with */
        Py_DECREF(self->string);
        self->string = NULL;
    }

    return obj;
}

static PyObject *
SignatureIter_tp_iter(PyObject *self)
{
    Py_INCREF(self);
    return self;
}

static PyTypeObject SignatureIterType = {
    PyObject_HEAD_INIT(DEFERRED_ADDRESS(&PyType_Type))
    0,
    "_dbus_bindings._SignatureIter",
    sizeof(SignatureIter),
    0,
    (destructor)SignatureIter_tp_dealloc,   /* tp_dealloc */
    0,                                      /* tp_print */
    0,                                      /* tp_getattr */
    0,                                      /* tp_setattr */
    0,                                      /* tp_compare */
    0,                                      /* tp_repr */
    0,                                      /* tp_as_number */
    0,                                      /* tp_as_sequence */
    0,                                      /* tp_as_mapping */
    0,                                      /* tp_hash */
    0,                                      /* tp_call */
    0,                                      /* tp_str */
    0,                                      /* tp_getattro */
    0,                                      /* tp_setattro */
    0,                                      /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                     /* tp_flags */
    0,                                      /* tp_doc */
    0,                                      /* tp_traverse */
    0,                                      /* tp_clear */
    0,                                      /* tp_richcompare */
    0,                                      /* tp_weaklistoffset */
    SignatureIter_tp_iter,                  /* tp_iter */
    (iternextfunc)SignatureIter_tp_iternext,  /* tp_iternext */
    0,                                      /* tp_methods */
    0,                                      /* tp_members */
    0,                                      /* tp_getset */
    0,                                      /* tp_base */
    0,                                      /* tp_dict */
    0,                                      /* tp_descr_get */
    0,                                      /* tp_descr_set */
    0,                                      /* tp_dictoffset */
    0,                                      /* tp_init */
    0,                                      /* tp_alloc */
    /* deliberately not callable! Use iter(Signature) instead */
    0,                                      /* tp_new */
    0,                                      /* tp_free */
};

static PyObject *
Signature_tp_iter (PyObject *self)
{
    SignatureIter *iter = PyObject_New(SignatureIter, &SignatureIterType);
    if (!iter) return NULL;

    if (PyString_AS_STRING (self)[0]) {
        Py_INCREF(self);
        iter->string = self;
        dbus_signature_iter_init(&(iter->iter), PyString_AS_STRING(self));
    }
    else {
        /* this is a null string, make a null iterator */
        iter->string = NULL;
    }
    return (PyObject *)iter;
}

static PyObject *
Signature_tp_new (PyTypeObject *cls, PyObject *args, PyObject *kwargs)
{
    const char *str = NULL;
    PyObject *ignored;
    static char *argnames[] = {"object_path", "variant_level", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s|O:__new__", argnames,
                                     &str, &ignored)) return NULL;
    if (!dbus_signature_validate(str, NULL)) {
        PyErr_SetString(PyExc_ValueError, "Corrupt type signature");
        return NULL;
    }
    return (DBusPyStrBase_Type.tp_new)(cls, args, kwargs);
}

static PyTypeObject DBusPySignature_Type = {
    PyObject_HEAD_INIT(DEFERRED_ADDRESS(&PyType_Type))
    0,
    "dbus.Signature",
    0,
    0,
    0,                                      /* tp_dealloc */
    0,                                      /* tp_print */
    0,                                      /* tp_getattr */
    0,                                      /* tp_setattr */
    0,                                      /* tp_compare */
    0,                                      /* tp_repr */
    0,                                      /* tp_as_number */
    0,                                      /* tp_as_sequence */
    0,                                      /* tp_as_mapping */
    0,                                      /* tp_hash */
    0,                                      /* tp_call */
    0,                                      /* tp_str */
    0,                                      /* tp_getattro */
    0,                                      /* tp_setattro */
    0,                                      /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    Signature_tp_doc,                       /* tp_doc */
    0,                                      /* tp_traverse */
    0,                                      /* tp_clear */
    0,                                      /* tp_richcompare */
    0,                                      /* tp_weaklistoffset */
    Signature_tp_iter,                      /* tp_iter */
    0,                                      /* tp_iternext */
    0,                                      /* tp_methods */
    0,                                      /* tp_members */
    0,                                      /* tp_getset */
    DEFERRED_ADDRESS(&DBusPythonStringType), /* tp_base */
    0,                                      /* tp_dict */
    0,                                      /* tp_descr_get */
    0,                                      /* tp_descr_set */
    0,                                      /* tp_dictoffset */
    0,                                      /* tp_init */
    0,                                      /* tp_alloc */
    Signature_tp_new,                       /* tp_new */
    0,                                      /* tp_free */
};

PyObject *
DBusPySignature_FromStringObject(PyObject *o, int allow_none)
{
    if (allow_none && o == Py_None) {
        Py_INCREF(o);
        return o;
    }
    if (PyObject_TypeCheck(o, &DBusPySignature_Type)) {
        Py_INCREF(o);
        return o;
    }
    return PyObject_CallFunction((PyObject *)&DBusPySignature_Type, "(O)", o);
}

PyObject *
DBusPySignature_FromStringAndVariantLevel(const char *str, long variant_level)
{
    return PyObject_CallFunction((PyObject *)&DBusPySignature_Type, "(sl)",
                                 str, variant_level);
}

PyObject *
DBusPySignature_FromStringAndSize(const char *str, Py_ssize_t size)
{
    return PyObject_CallFunction((PyObject *)&DBusPySignature_Type, "(s#)",
                                 str, size);
}

PyObject *
DBusPySignature_FromString(const char *str)
{
    return PyObject_CallFunction((PyObject *)&DBusPySignature_Type, "(s)",
                                 str);
}

int
DBusPySignature_Check(PyObject *o)
{
    return PyObject_TypeCheck(o, &DBusPySignature_Type);
}

dbus_bool_t
dbus_py_init_signature(void)
{
    if (PyType_Ready(&SignatureIterType) < 0) return 0;

    DBusPySignature_Type.tp_base = &DBusPyStrBase_Type;
    if (PyType_Ready(&DBusPySignature_Type) < 0) return 0;
    DBusPySignature_Type.tp_print = NULL;

    return 1;
}

dbus_bool_t
dbus_py_insert_signature(PyObject *this_module)
{
    Py_INCREF(&DBusPySignature_Type);
    if (PyModule_AddObject(this_module, "Signature",
                           (PyObject *)&DBusPySignature_Type) < 0) return 0;
    Py_INCREF(&SignatureIterType);
    if (PyModule_AddObject(this_module, "_SignatureIter",
                           (PyObject *)&SignatureIterType) < 0) return 0;

    return 1;
}

/* vim:set ft=c cino< sw=4 sts=4 et: */
