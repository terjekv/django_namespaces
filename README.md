# Django Namespaces

![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)
![Tests](https://github.com/terjekv/hubuum/actions/workflows/tox.yml/badge.svg)
![Lint](https://github.com/terjekv/hubuum/actions/workflows/lint.yml/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/terjekv/django_namespace_permissions/badge.svg?branch=main)](https://coveralls.io/github/terjekv/django_namespace_permissions?branch=main)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/35503ba680e246ccb1f059d3646be7d0)](https://app.codacy.com/gh/terjekv/django_namespace_permissions/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

## Concept

A collection-oriented object permission model for Django.

Namespaces fills the niche when you want to grant groups or users privileges to collections of objects, rather than being concerned about permissions for each individual object.

## What is a namespace?

- A namespace contains a collection of objects.
- Every object belongs to one and only one namespace.
- Users and/or groups may be granted permissions to namespace.
- Permissions to create into, read, update, and delete objects within a namespace are delegated to users and/or groups.
- A users permissions to a namespace are the set of permissons granted to the user directly, as well as the permissions granted to groups the user is a member of.
- There is a clear distinction between permissions to the namespace itself and the objects within, allowing for a clear distinction between administration of the namespace and administration of the objects within.
- A specific permission (delegate) can be granted to a user or group to a namespace, they can then grant object permissions to other users and groups.
